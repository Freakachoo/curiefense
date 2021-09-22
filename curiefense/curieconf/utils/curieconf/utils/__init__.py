import codecs
import base64
import json
import pydash
from copy import deepcopy
from flask import current_app

DOCUMENTS_PATH = {
    "ratelimits": "config/json/limits.json",
    "ratelimitprofiles": "config/json/limitprofiles.json",
    "securitypolicies": "config/json/securitypolicy.json",
    "wafrules": "config/json/waf-signatures.json",
    "wafpolicies": "config/json/waf-profiles.json",
    "aclprofiles": "config/json/acl-profiles.json",
    "globalfilters": "config/json/globalfilter-lists.json",
    "flowcontrol": "config/json/flow-control.json",
}

BLOBS_PATH = {
    "geolite2asn": "config/maxmind/GeoLite2-ASN.mmdb",
    "geolite2country": "config/maxmind/GeoLite2-Country.mmdb",
    "geolite2city": "config/maxmind/GeoLite2-City.mmdb",
}

BLOBS_BOOTSTRAP = {
    "geolite2asn": b"",
    "geolite2country": b"",
    "geolite2city": b"",
}


def vconvert(conf_type_name, vfrom):
    """
    Convert configuration types terminology from demand API version to
    the actual one. It is needed to support multiple API versions in parallel.

    Args:
        conf_type_name (string): Configuration type to convert.
        vfrom (string): Version of the API from which to convert.

    Returns
        string: converted conf type
    """
    apimap = {
        "v1": {
            "urlmaps": "securitypolicies",
            "wafrules": "contentfilterrules",
            "wafpolicies": "contentfilterprofiles",
            "aclpolicies": "aclprofiles",
            "tagrules": "globalfilters",
            "flowcontrol": "flowcontrolpolicies",
        }
    }

    return pydash.get(apimap, f"{vfrom}.{conf_type_name}", conf_type_name)


def last_v1_rl_convert(document, *args):
    """
    Convert Rate Limit from Latest into V1 API format.
    Latest API (starting from V2) supports multiple thresholds (action + limit)
    for a one Rate Limit.
    The function takes only the first threshold element from the array.
    To support backward compatibility we limit V1 users to only one threshold.

    Args:
        document (dict): RL configuration document in Latest API format

    Returns:
        dict: converted to V1 format
    """
    v1 = deepcopy(document)
    v1["limit"] = pydash.get(v1, "thresholds[0].limit", "")
    v1["action"] = pydash.get(v1, "thresholds[0].action", {"type": "default"})
    del v1["thresholds"]
    return v1


def v1_last_rl_convert(v1_document, *args):
    """
    Convert Url Map from V1 into Latest API format.
    Latest API (starting from V2) supports multiple thresholds (action + limit)
    for a one Rate Limit.
    But V1 accepts only one limit and action. The function takes limit and action
    and add it as a one element of thresholds array.
    To support backward compatibility we limit V1 users to only one threshold.

    Args:
        v1_document (dict): RL configuration document in V1 format

    Returns:
        dict: converted to Latest format
    """
    vLast = deepcopy(v1_document)
    pydash.set_(
        vLast, "thresholds[0]", {"limit": vLast["limit"], "action": vLast["action"]}
    )
    del vLast["limit"]
    del vLast["action"]
    return vLast


def last_v1_urlmap_convert(document, params={"config": ""}, *args):
    """
    Convert Url Map from Latesl into V1 API format.
    Latlest API (starting from V2) supports of embedding Rate Limit Profiles only
    and doesn't allow to embed Rate Limit Rules directly.
    The function spread embedded RL Profiles into RL Rules and place it into output
    as a flat array of ids.

    Args:
        document (dict): RL configuration document in Latest API format
        params (dict): A 'config' - git commit hash of rate limit profiles

    Returns:
        dict: converted to V1 format
    """
    v1 = deepcopy(document)
    for map in v1["map"]:
        limit_ids = []
        for profile_id in pydash.get(map, "limit_profile_ids", []):
            profile = current_app.backend.entries_get(
                params["config"], "ratelimitprofiles", profile_id
            )
            if profile["limit_ids"]:
                limit_ids += profile["limit_ids"]
        map["limit_ids"] = limit_ids
        del map["limit_profile_ids"]
    return v1


def v1_last_urlmap_convert(v1_document, params={"config": ""}, *args):
    """
    Convert Url Map from V1 into Latest API format.
    Latlest API (starting from V2) supports of embedding only Rate Limit Profiles
    and doesn't allow to embed Rate Limit Rules directly.
    The function:
    1. Takes Rate Limit IDs from input, creates a new Rate Limit Profile
    per each map for the Security Policy with the id `sp_{sp_id}_{map_index}`.
    Or if it was already created - use the existing one.
    2. Embeds RL IDs there, and embeds the RL Profile ID into the Security Profile.

    Args:
        v1_document (dict): RL configuration document in V1 format
        params (dict): A 'config' - git commit hash of rate limit profiles

    Returns:
        dict: converted to Latest API format
    """
    vLast = deepcopy(v1_document)
    profiles = current_app.backend.documents_get(params["config"], "ratelimitprofiles")
    for map_index, map in enumerate(vLast["map"]):
        map_profile_id = f'sp_{vLast["id"]}_{map_index}'
        map_profile = pydash.find(profiles, lambda p: p["id"] == map_profile_id)
        if map_profile:
            pydash.set_(map_profile, "limit_ids", map["limit_ids"])
            current_app.backend.entries_update(
                params["config"], "ratelimitprofiles", map_profile_id, map_profile
            )
        else:
            map_profile = current_app.backend.entries_create(
                params["config"],
                "ratelimitprofiles",
                {
                    "id": map_profile_id,
                    "name": f'{vLast["name"]} Rate Limit Profile',
                    "description": "",
                    "limit_ids": map["limit_ids"],
                },
            )
        pydash.set_(map, "limit_profile_ids", [map_profile_id])
        del map["limit_ids"]
    return vLast


def vconfigconvert(ctype, doc, vfrom="last", vto="last", params={}):
    """
    Convert configuration documents structure from between API versions formats.

    Args:
        ctype (string): Configuration type to convert.
        doc (dict): configuration document
        vfrom (string): Version of the API from which to convert.
        vto (string): Version of the API to which version to convert.
        params (dict): Any additional parameters needed for convert functions.

    Returns:
        dict: converted config document or the original one if nothing to convert.
    """
    apimap = {
        "v1_last": {
            "ratelimits": v1_last_rl_convert,
            "urlmaps": v1_last_urlmap_convert,
        },
        "last_v1": {
            "ratelimits": last_v1_rl_convert,
            "urlmaps": last_v1_urlmap_convert,
        },
    }

    def do_not_convert(doc, *args):
        return doc

    convertfunc = pydash.get(apimap, f"{vfrom}_{vto}.{ctype}", do_not_convert)
    return convertfunc(doc, params)


def delete_embedded_rl_profiles(config, urlmap_id):
    """
    Delete Rate Limit Profiles embedded into a Url Map.
    Because V1 creates Rate Limit Profiles automatically per Url Map map and
    because V1 API does't have an interface to work with the Profiles, we need
    to clean it when Url Map is deleted.

    Args:
        config (string): git commit hash of the url map
        urlmap_id (string): id of the deleted url map

    Returns:
        throws error or nothing returned
    """
    urlmap = current_app.backend.entries_get(
        config, vconvert("urlmaps", "v1"), urlmap_id
    )
    for map in urlmap["map"]:
        for profile_id in map["limit_profile_ids"]:
            current_app.backend.entries_delete(config, "ratelimitprofiles", profile_id)


def jblob2bytes(jblob):
    fmt = jblob["format"]
    jraw = jblob["blob"]
    if fmt == "json":
        return json.dumps(jraw).encode("utf8")
    elif fmt == "string":
        return jraw.encode("utf8")
    elif fmt == "base64" or fmt.endswith("+base64"):
        jraw = codecs.decode(jraw.encode("utf8"), "base64")
        if "+" in fmt:
            cmp, b = fmt.rsplit("+", 1)
            if cmp not in ["zip", "bz2"]:
                raise Exception("unknown blob format: [%s]" % fmt)
            jraw = codecs.decode(jraw, cmp)
        return jraw
    raise Exception("unknown blob format: [%s]" % fmt)


def bytes2jblob(b, fmthint=None):
    try:
        if fmthint == "json":
            c = json.loads(b.decode("utf-8"))
            return {"format": "json", "blob": c}
    except:
        pass
    compb = codecs.encode(b, "bz2")
    if len(compb) < len(b):
        b = compb
        fmt = "bz2+base64"
    else:
        fmt = "base64"
    bl = base64.b64encode(b).decode("utf-8")
    return {"format": fmt, "blob": bl}
