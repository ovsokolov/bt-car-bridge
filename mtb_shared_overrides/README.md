Tracked patches for local ModusToolbox dependencies.

The `mtb_shared/` directories are ignored because they are fetched vendor
content. If a project needs a narrow SDK adapter, keep the source edit in the
local `mtb_shared/` tree for testing and mirror it here as a patch so another
machine can reproduce the same build.

Apply AG patches from `C:\BT_Projects` after dependencies are present:

```powershell
git apply mtb_shared_overrides/headset_hfp_uart_ag/btsdk-audio-release-v4.9.5.patch
```
