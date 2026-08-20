# Koma – Hide Apps Menu (`koma_lock_apps`)

Data-only Odoo 19 module that hides the **Apps** store and the module installer
so regular users — and administrators in normal (non-developer) mode — cannot
install new modules such as Website, CRM, Sales, etc.

It is **fully reversible** and modifies no Odoo source files. It only re-assigns
two menus to `base.group_no_one`, a group that is active only in Developer Mode.

## What it hides

| Menu | XML id |
|------|--------|
| Top-level **Apps** store | `base.menu_management` |
| The module installer list | `base.menu_module_tree` |

Hiding the top-level `menu_management` also hides everything nested under it
(Apps, Third-Party Apps, Theme Store). The installer list is restricted too as a
belt-and-suspenders measure.

## Where it lives

Mounted into the Odoo container via `docker-compose.yml`:

```
./addons  ->  /mnt/extra-addons   (addons_path includes /mnt/extra-addons)
```

so the module folder is `eSante/odoo/addons/koma_lock_apps/`.

## Install

Run from `eSante/odoo/` (where `docker-compose.yml` lives):

```powershell
# One-off run that installs the module into the odopk DB, then exits
docker compose run --rm odoo odoo -c /etc/odoo/odoo.conf -d odopk -i koma_lock_apps --stop-after-init

# Restart the stack so odoo.conf (list_db=False) is in effect
docker compose up -d
```

After this, the **Apps** menu and *Settings → Technical → Apps* are gone.

## Update (after editing the module)

```powershell
docker compose run --rm odoo odoo -c /etc/odoo/odoo.conf -d odopk -u koma_lock_apps --stop-after-init
docker compose up -d
```

## Uninstall / reverse

Any one of these brings the Apps menu back:

- **Uninstall the module** (via command line, since the Apps UI is hidden):
  ```powershell
  docker compose run --rm odoo odoo -c /etc/odoo/odoo.conf -d odopk --uninstall koma_lock_apps --stop-after-init
  docker compose up -d
  ```
- **Temporarily**: activate Developer Mode
  (*Settings → General Settings → Developer Tools → Activate the developer mode*).
  `group_no_one` becomes active, so the menus reappear for your session.

## Related hardening (not part of this module)

These live in `eSante/odoo/odoo.conf`:

- `list_db = False` — hides the database manager so nobody can create a fresh DB
  with every app installable. Set back to `True` to reverse.
- `dbfilter = ^odopk$` — pins the container to the `odopk` database.
- `admin_passwd` — master password gating the DB manager. **Change from the
  default before production.**

The strongest per-user control is still access rights: in **Settings → Users**,
leave **Administration** blank (not "Settings") for staff accounts so they never
see the Apps or Settings menus at all.

---

- **Version:** 19.0.1.0.0
- **License:** LGPL-3
- **Depends:** `base`
