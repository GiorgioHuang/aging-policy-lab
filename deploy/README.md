# Deploy notes

## Artifact Registry size / cleanup

Every deploy pushes a new container image to the Artifact Registry repo
`cloud-run-source-deploy` (region `us-east1`). Old images are **not** deleted
automatically, so after dozens of builds the repo grows to several GB even though
each image is only ~150–250 MB. This is accumulation, not a single large image.

### One-time: reclaim space now

Set a cleanup policy (keeps the 5 most recent versions, deletes anything older
than 30 days) and let it prune. **Dry-run first** to see what it would delete:

```bash
# preview
gcloud artifacts repositories set-cleanup-policies cloud-run-source-deploy \
  --location=us-east1 \
  --policy=deploy/artifact-cleanup-policy.json \
  --dry-run

# apply (removes --dry-run)
gcloud artifacts repositories set-cleanup-policies cloud-run-source-deploy \
  --location=us-east1 \
  --policy=deploy/artifact-cleanup-policy.json
```

Prefer to bulk-delete immediately instead of waiting for the policy? List and
delete old digests, keeping the newest few:

```bash
gcloud artifacts docker images list \
  us-east1-docker.pkg.dev/PROJECT_ID/cloud-run-source-deploy/hapi-web \
  --include-tags --sort-by=~UPDATE_TIME --format='value(version)' \
| tail -n +6 \
| xargs -I{} gcloud artifacts docker images delete \
    "us-east1-docker.pkg.dev/PROJECT_ID/cloud-run-source-deploy/hapi-web@{}" \
    --delete-tags --quiet
```

(Replace `PROJECT_ID`. Cloud Run keeps the image its current revision uses; don't
delete that digest — the `tail -n +6` keeps the 5 newest, which covers it.)

### Ongoing

With the cleanup policy set, the repo self-prunes to ~5 recent images. See
`../cloudbuild.yaml` for the build that produces them (tagged by commit SHA).
