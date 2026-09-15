# HC branch

This branch contains the complete VentureAI repository plus the CareAI project
under `CareAI/`.

- CareAI source repository: `https://github.com/Qifang24/CareAI.git`
- Imported CareAI commit: `038d329f36ebe2bbb3ed5ce70331eff3953fdc1c`
- Import form: ordinary tracked files, not a Git submodule
- Excluded local artifacts: `.git`, `.env`, virtual environments,
  `node_modules`, build output and local databases

Keeping CareAI as ordinary files means a clone of the `HC` branch contains both
projects immediately and does not require a separate submodule checkout.
