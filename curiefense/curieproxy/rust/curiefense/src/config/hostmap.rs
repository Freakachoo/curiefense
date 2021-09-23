use crate::config::limit::{Limit, LimitProfile};
use crate::config::raw::AclProfile;
use crate::config::utils::Matching;
use crate::config::waf::WafProfile;

/// the default entry is statically encoded so that it is certain it exists
#[derive(Debug, Clone)]
pub struct HostMap {
    pub id: String,
    pub name: String,
    pub entries: Vec<Matching<SecurityPolicy>>,
    pub default: Option<SecurityPolicy>,
}

/// a map entry, with links to the acl and waf profiles
#[derive(Debug, Clone)]
pub struct SecurityPolicy {
    pub name: String,
    pub acl_active: bool,
    pub acl_profile: AclProfile,
    pub waf_active: bool,
    pub waf_profile: WafProfile,
    pub limits: Vec<Limit>,
    pub limit_profiles: Vec<LimitProfile>,
}
