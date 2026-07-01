/**
 * Shared, non-secret site constants. The maintainer's *personal email is
 * deliberately never stored here or shipped to the client* — contact goes
 * through GitHub (public, timely) or the private DB-backed form (see
 * lib/contact.ts). Only the public GitHub profile / repo links are exposed.
 */
export const GITHUB_USER = "GiorgioHuang";
export const GITHUB_REPO = "aging-policy-lab";

export const GITHUB_PROFILE_URL = `https://github.com/${GITHUB_USER}`;
export const GITHUB_REPO_URL = `https://github.com/${GITHUB_USER}/${GITHUB_REPO}`;
export const GITHUB_NEW_ISSUE_URL = `${GITHUB_REPO_URL}/issues/new`;
export const GITHUB_DISCUSSIONS_URL = `${GITHUB_REPO_URL}/discussions`;
