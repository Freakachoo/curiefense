import pytest
from curieconf import utils
import json
import codecs
import base64
from copy import deepcopy
import mock

binvec_hex = (
    "b70a1da09a4998bd56b083d76bf528053c9b924bbb07168792151a5a177bbaa232949a8600bcb2"
    + "5fffd487db3602aa77a5ac96441739be889f614f8e24cef51e487b36e4e2659a12b5c6de8cf0cd"
)

binvec = codecs.decode(binvec_hex, "hex")
binvec_b64 = base64.b64encode(binvec).decode("utf-8")
binvec_b64_nl = codecs.encode(binvec, "base64").decode("utf-8")
binvec_zip = base64.b64encode(codecs.encode(binvec, "zip")).decode("utf-8")
binvec_bz2 = base64.b64encode(codecs.encode(binvec, "bz2")).decode("utf-8")

jsonvec = [{"foo": "bar", "test": 6}, 42, True, "foobarboofar"]


@pytest.mark.parametrize(
    "fmt,blob",
    [
        ("base64", binvec_b64),
        ("base64", binvec_b64_nl),
        ("bz2+base64", binvec_bz2),
        ("zip+base64", binvec_zip),
    ],
)
def test_jblob2bytes_bin(fmt, blob):
    res = utils.jblob2bytes(
        {
            "format": fmt,
            "blob": blob,
        }
    )
    assert res == binvec


def test_jblob2bytes_json():
    res = utils.jblob2bytes({"format": "json", "blob": jsonvec})
    decjson = json.loads(res.decode("utf-8"))
    assert decjson == jsonvec


def test_bytes2jblob_json():
    vec = json.dumps(jsonvec).encode("utf8")
    res = utils.bytes2jblob(vec, fmthint="json")
    assert res == {"format": "json", "blob": jsonvec}

    vec_b64 = base64.b64encode(vec).decode("utf8")
    res = utils.bytes2jblob(vec)
    assert res == {"format": "base64", "blob": vec_b64}

    vec = b'{ "abc": 456, "broken json }'
    vec_b64 = base64.b64encode(vec).decode("utf8")
    res = utils.bytes2jblob(vec, fmthint="json")
    assert res == {"format": "base64", "blob": vec_b64}


def test_bytes2jblob_json():
    vec = b"A" * 500
    res = utils.bytes2jblob(vec)
    assert res == {
        "format": "bz2+base64",
        "blob": "QlpoOTFBWSZTWYtV77YAAACEAKAAIAggACEmQZioDi7kinChIRar32w=",
    }
    res2 = utils.jblob2bytes(res)
    assert res2 == vec


@mock.patch.object(utils, "current_app")
def test_last_v1_urlmap_convert(test_current_app):
    docV2 = {
        "id": "1",
        "name": "default entry",
        "match": "__default__",
        "map": [
            {
                "limit_profile_ids": ["limit_id_1", "limit_id_2"],
                "name": "default",
                "match": "/",
            },
            {"limit_profile_ids": ["limit_id_3"], "name": "default", "match": "/"},
        ],
    }
    # `limit_ids` for 3 embedded profiles. Per each call of 'entries_get' function.
    test_current_app.backend.entries_get.side_effect = [
        {"limit_ids": ["123", "345"]},
        {"limit_ids": ["567"]},
        {"limit_ids": ["222"]},
    ]

    docV1 = deepcopy(docV2)
    # expect it removes 'limit_profile_ids'
    del docV1["map"][0]["limit_profile_ids"]
    del docV1["map"][1]["limit_profile_ids"]
    # expect it exchanges 'limit_profile_ids' to all 'limit_ids' from the profiles
    docV1["map"][0]["limit_ids"] = ["123", "345", "567"]
    docV1["map"][1]["limit_ids"] = ["222"]
    assert utils.last_v1_urlmap_convert(docV2, {"config": "master"}) == docV1


@mock.patch.object(utils, "current_app")
def test_v1_last_urlmap_convert(test_current_app):
    docV1 = {
        "id": "urlmap_id",
        "name": "default entry",
        "match": "__default__",
        "map": [
            {
                # this map will update sp_urlmap_id_0
                "limit_ids": ["123", "345", "567"],
                "name": "default",
                "match": "/",
            },
            {
                # this map will update sp_urlmap_id_1
                "limit_ids": ["222"],
                "name": "default",
                "match": "/",
            },
            {
                # this map will create new sp_urlmap_id_2
                "limit_ids": ["1"],
                "name": "default",
                "match": "/",
            },
        ],
    }

    test_current_app.backend.documents_get.return_value = [
        # profile without "567" - will expect to be added.
        {"id": "sp_urlmap_id_0", "limit_ids": ["123", "345"]},
        # profile with additional "111" - will expect to be deleted from the list.
        {"id": "sp_urlmap_id_1", "limit_ids": ["222", "111"]},
    ]

    docV2 = deepcopy(docV1)
    # expect limit_ids exchanged to existing profile ids
    docV2["map"] = [
        {"limit_profile_ids": ["sp_urlmap_id_0"], "match": "/", "name": "default"},
        {"limit_profile_ids": ["sp_urlmap_id_1"], "match": "/", "name": "default"},
        # a new profile was created
        {"limit_profile_ids": ["sp_urlmap_id_2"], "match": "/", "name": "default"},
    ]

    res = utils.v1_last_urlmap_convert(docV1, {"config": "master"})
    assert res == docV2
    # expect updated only two profiles
    assert len(test_current_app.backend.entries_update.call_args_list) == 2
    # and created one
    assert len(test_current_app.backend.entries_create.call_args_list) == 1

    assert test_current_app.backend.entries_update.call_args_list[0][0] == (
        "master",
        "ratelimitprofiles",
        "sp_urlmap_id_0",
        {"id": "sp_urlmap_id_0", "limit_ids": ["123", "345", "567"]},
    )
    assert test_current_app.backend.entries_update.call_args_list[1][0] == (
        "master",
        "ratelimitprofiles",
        "sp_urlmap_id_1",
        {"id": "sp_urlmap_id_1", "limit_ids": ["222"]},
    )
    assert test_current_app.backend.entries_create.call_args_list[0][0] == (
        # expect the new name generated by pattern '{docV1["name"]} Rate Limit Profile'
        "master",
        "ratelimitprofiles",
        {
            "id": "sp_urlmap_id_2",
            "name": "default entry Rate Limit Profile",
            "description": "",
            "limit_ids": ["1"],
        },
    )
