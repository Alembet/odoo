# Deployment notes — Apps lockdown (odopk)

Companion to the `koma_lock_apps` module. Records the **server-side changes**
that live in `odoo.conf`. `odoo.conf` is intentionally **git-ignored** (it holds
the database-manager master password in plaintext), so those values are not in
the repo — this file documents them instead.

## Changes applied to `eSante/odoo/odoo.conf`

| Key | Before | After | Why |
|-----|--------|-------|-----|
| `list_db` | `True` | `False` | Hide the database manager/selector so nobody can create a fresh DB (which would come with every app installable) or backup/restore/delete existing ones. |
| `dbfilter` | *(unset)* | `^odopk$` | Pin this container to the single Koma database. |
| `admin_passwd` | `admin` (default) | *strong random 32-char value — **redacted**, stored in `odoo.conf` on the host + the team password manager* | The default value makes Odoo treat the DB manager as "insecure" and lets anyone claim the master password / create databases. A strong value closes that. |

> The actual master password is **not** recorded here by design. It is in
> `odoo.conf` on the server and should also be kept in the password manager.

## How the two layers work together

- **`koma_lock_apps` module** (in git) — hides the **Apps** store menus
  (`base.menu_management`, `base.menu_module_tree`) from admins in normal mode.
- **`odoo.conf`** (not in git) — locks the database manager and pins the DB.
- **Per-user access rights** — leave *Administration* blank on staff accounts so
  they never see Apps or Settings.

## Applying / reverting the config

After editing `odoo.conf`, recreate the odoo container so it reloads:

```powershell
cd eSante/odoo
docker compose up -d --force-recreate odoo
```

To reverse the DB-manager lockdown: set `list_db = True` (and optionally clear
`dbfilter`) and recreate the container. To rotate the master password, change
`admin_passwd` and recreate.

## Verification performed (2026-08-20)

Checked via the web client's own `/web/webclient/load_menus` endpoint:

- Admin, normal mode: Apps store **hidden**.
- Staff user (non-admin): Apps store **and** Settings **hidden**.
- Developer Mode: Apps store **reappears** (expected, reversible escape hatch).
- Live `odoo.conf` in the running container confirmed `list_db = False`,
  `dbfilter = ^odopk$`.
