# odoo-pwa — Implementation Guide

**Rewriting the Odoo experience as a PWA over the Odoo JSON-RPC API, surfaced inside `koma-spa`,
and extended with a Gabon-specific HR & Payroll engine (Polyclinique Koma, Libreville).**

> Scope agreed with the team: **(1)** keep the Odoo backend as-is and build a new Progressive Web
> App frontend over its API, **(4)** integrate that frontend into the existing `koma-spa` React SPA
> + Python-sidecar architecture, and **add new HR/Payroll features** driven by the source PDF
> *"Outils RH et Paie Open Source France"*. Domain coverage bridges the **already-installed ERP apps**
> (Sales, Inventory, Purchase, CRM, POS, Website) with a **new HR/Paie module** for Gabon.

> ⚠️ **Legal / accuracy caveat (carried from the source PDF).** The Gabonese payroll rules below
> (CNSS, CNAMGS, FNH, TCS, IRPP) are transcribed from the PDF and are **decision-support only**.
> Rates and the exact base-ordering **must be validated with a local expert-comptable / ESN in
> Libreville** and against the current *Code Général des Impôts* and *Code du travail gabonais*
> before any real bulletin de paie is issued. Treat every formula here as a configurable default,
> never a certified calculation.

---

## 0. TL;DR — what you are building

```
┌────────────────────────────────────────────────────────────────────────────┐
│  koma-spa  (Vite + React 19 SPA, PWA-enabled)                                │
│  ├─ /staff/erp        → Sales · Inventory · Purchase · CRM · POS dashboards  │
│  ├─ /staff/hr         → employees, contracts, congés, gardes/astreintes      │
│  └─ /staff/paie       → Gabon payroll: bulletins, CNSS/CNAMGS/TCS/IRPP       │
│        │  installable / offline (service worker + manifest = the "PWA")      │
└────────┼─────────────────────────────────────────────────────────────────────┘
         │  HTTPS / JSON  (VITE_ODOO_URL, default http://localhost:8030)
┌────────▼─────────────────────────────────────────────────────────────────────┐
│  odoo-service   (FastAPI sidecar, port 8030)  ← NEW, 14th sidecar             │
│  ├─ thin JSON-RPC proxy to Odoo (auth, session, model.method whitelisting)    │
│  ├─ Gabon payroll engine (pure-python, unit-tested, the PDF's rules)          │
│  └─ maps koma-spa Auth0 / Keycloak identity → Odoo uid                        │
└────────┼─────────────────────────────────────────────────────────────────────┘
         │  JSON-RPC 2.0  (/jsonrpc, /web/session/authenticate)
┌────────▼─────────────────────────────────────────────────────────────────────┐
│  Odoo 19 Community  (docker: odoo:19 + postgres:16)  ← ALREADY RUNNING        │
│  DB "odopk": sale_management, stock, purchase, crm, point_of_sale, website    │
│  + to install: hr, hr_holidays, hr_attendance, hr_work_entry, hr_skills       │
│  + custom addon: l10n_ga_hr (Gabon employee fields + planning gardes)         │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Why a sidecar carries the payroll, not Odoo itself:** this Odoo 19 Community install **ships no
payroll module** (`hr_payroll` is Enterprise-only; the OCA `om_hr_payroll` the PDF names is not
vendored here). Rather than depend on a third-party payroll addon, the Gabon rules live in the
`odoo-service` sidecar as tested pure-python — versionable, unit-testable, and consistent with how
the other thirteen `koma-spa` sidecars own their domain logic (billing, lab, imaging, …).

---

## 1. Current state (already done)

The Odoo backend is deployed and running via `eSante/odoo/docker-compose.yml`:

| Component | Detail |
|---|---|
| Odoo | `odoo:19`, web on **8069**, longpolling on 8072 |
| Postgres | `postgres:16`, user/pass `odoo`/`odoo` |
| Database | **`odopk`**, admin login `admin` / `admin`, master pwd `admin` |
| Installed apps | `sale_management`, `stock`, `purchase`, `crm`, `point_of_sale`, `website` (+ `account`, `product` deps) |
| Demo data | **loaded** (`--with-demo`); 79 products, 44 contacts, 24 SO, 11 PO, 44 leads, 49 stock moves |

Operational notes learned during deployment (keep these in the runbook):

- **Odoo 19 changed the demo default** — `--with-demo` now defaults to *False*. Create demo DBs
  explicitly: `odoo -d <db> --with-demo -i <modules> --stop-after-init`.
- **Never restart the container mid database-creation** — it corrupts the half-initialised DB
  (`KeyError: 'ir.http'`). Let the web "Loading…" finish, or init from the CLI with
  `--stop-after-init` (uninterruptible).
- Module installs need exclusive DB access: `docker compose stop odoo` first, then
  `docker compose run --rm odoo odoo -c /etc/odoo/odoo.conf -d odopk -i <mods> --stop-after-init`,
  then `docker compose up -d odoo`.
- On Windows/Git-Bash, prefix container paths with `MSYS_NO_PATHCONV=1` so `/etc/odoo/odoo.conf`
  isn't mangled to `C:/Program Files/Git/etc/...`.

---

## 2. Phase A — Odoo backend: add the HR foundation

These modules **are** in this Community build (verified: all `uninstalled`, installable). Payroll is
deliberately *not* installed in Odoo — it is provided by the sidecar (Phase C).

```bash
cd C:/Users/getic/Downloads/geticx/eSante/odoo
docker compose stop odoo
MSYS_NO_PATHCONV=1 docker compose run --rm odoo \
  odoo -c /etc/odoo/odoo.conf -d odopk --with-demo \
  -i hr,hr_holidays,hr_attendance,hr_work_entry,hr_skills,hr_recruitment,project \
  --stop-after-init
docker compose up -d odoo
```

| Module | Role in the clinic |
|---|---|
| `hr` | Employee registry (dossiers salariés, diplômes via `hr_skills`) |
| `hr` (via `hr.version`) | Contracts, wage, start/end — the payroll input. **Odoo 19 merged the old `hr_contract` module into `hr`**; contract/wage data now lives on the `hr.version` model, no separate module to install. |
| `hr_holidays` | Congés (leave types, balances, approval) |
| `hr_attendance` | Pointage des gardes (check-in/out; badge/biometric via API later) |
| `hr_work_entry` | Work-entry types → night/holiday premiums feed payroll variables |
| `hr_skills` | Certifications & compétences médicales |
| `hr_recruitment` | Recrutement (optional, from the PDF's "gestion des talents") |

### 2.1 Custom addon `l10n_ga_hr` (Gabon localisation, thin)

Instead of dev-mode Studio fields (which don't survive as code), add a small addon under
`eSante/odoo/addons/l10n_ga_hr/`. It only adds **data fields + planning helpers** — no payroll
compute (that's the sidecar's job, testable in isolation).

```
addons/l10n_ga_hr/
├── __manifest__.py
├── models/
│   └── hr_employee.py
├── security/ir.model.access.csv
└── views/hr_employee_views.xml
```

`__manifest__.py`
```python
{
    "name": "Gabon HR Localisation (Polyclinique Koma)",
    "version": "19.0.1.0.0",
    "depends": ["hr"],
    "author": "Getic X / Polyclinique Koma",
    "license": "LGPL-3",
    "category": "Human Resources/Localization",
    "data": ["security/ir.model.access.csv", "views/hr_employee_views.xml"],
}
```

`models/hr_employee.py`
```python
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    x_cnss = fields.Char(string="N° CNSS")
    x_cnamgs = fields.Char(string="N° CNAMGS")
    x_parts_irpp = fields.Float(string="Parts IRPP (quotient familial)", default=1.0)
    # Medical-staff planning inputs (feed payroll premiums)
    x_is_soignant = fields.Boolean(string="Personnel soignant (gardes 24/7)")
```

`security/ir.model.access.csv` — no new model, so this file can be a single header line (fields on
an existing model inherit its ACLs). Keep the file present so the manifest loads cleanly.

Install it:
```bash
docker compose stop odoo
MSYS_NO_PATHCONV=1 docker compose run --rm odoo \
  odoo -c /etc/odoo/odoo.conf -d odopk -i l10n_ga_hr --stop-after-init
docker compose up -d odoo
```

> The `./addons` mount is **read-only** (`:ro` in compose) — that's fine for loading, but to edit &
> reload during development either flip it to read-write or `docker compose restart odoo -u l10n_ga_hr`
> after each change (`-u` upgrades the module).

---

## 3. Phase B — the `odoo-service` bridge sidecar (port 8030)

Follows the exact pattern of the existing thirteen sidecars (FastAPI, `VITE_*_URL`, per-domain).
It is the **only** thing the browser talks to for ERP data — the browser never hits Odoo directly
(keeps Odoo off the public network, centralises auth, and lets us whitelist model/method access).

```
koma-spa/odoo-service/
├── app/
│   ├── main.py            # FastAPI app, CORS, routers
│   ├── odoo_client.py     # JSON-RPC session to Odoo
│   ├── auth.py            # Auth0/Keycloak → Odoo uid mapping
│   ├── routers/
│   │   ├── erp.py         # read-through: sales, stock, purchase, crm, pos
│   │   ├── hr.py          # employees, contracts, congés, attendances
│   │   └── paie.py        # payroll engine endpoints
│   └── payroll/
│       ├── gabon.py       # THE payroll engine (pure python, no Odoo import)
│       └── rates.py       # CNSS/CNAMGS/FNH/TCS/IRPP constants (config)
├── tests/
│   └── test_gabon_payroll.py
├── requirements.txt       # fastapi, uvicorn, httpx, pydantic
└── Dockerfile
```

### 3.1 JSON-RPC client (`odoo_client.py`)

Odoo exposes JSON-RPC at `/jsonrpc` and web-session auth at `/web/session/authenticate`. Use the
`call` → `object.execute_kw(db, uid, pwd, model, method, args, kwargs)` shape.

```python
import httpx

ODOO_URL = "http://odoo:8069"   # inside the compose network; or http://localhost:8069 in dev
ODOO_DB = "odopk"


class OdooRPC:
    def __init__(self, url=ODOO_URL, db=ODOO_DB):
        self.url, self.db = url, db
        self._client = httpx.AsyncClient(timeout=30)

    async def _call(self, service, method, args):
        payload = {"jsonrpc": "2.0", "method": "call",
                   "params": {"service": service, "method": method, "args": args}, "id": 1}
        r = await self._client.post(f"{self.url}/jsonrpc", json=payload)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(data["error"]["data"].get("message", data["error"]))
        return data["result"]

    async def login(self, login, password):
        return await self._call("common", "authenticate", [self.db, login, password, {}])

    async def execute_kw(self, uid, password, model, method, args, kwargs=None):
        return await self._call(
            "object", "execute_kw",
            [self.db, uid, password, model, method, args, kwargs or {}])
```

### 3.2 Read-through ERP endpoints (`routers/erp.py`)

Whitelist the models/methods the PWA may reach. Example — sales & inventory tiles:

```python
from fastapi import APIRouter, Depends
router = APIRouter(prefix="/erp", tags=["erp"])

READ_WHITELIST = {
    "sale.order": ["search_read"],
    "purchase.order": ["search_read"],
    "crm.lead": ["search_read"],
    "stock.picking": ["search_read"],
    "pos.order": ["search_read"],
    "product.template": ["search_read"],
}

@router.get("/sales")
async def sales(limit: int = 20, ctx=Depends(odoo_ctx)):
    return await ctx.rpc.execute_kw(
        ctx.uid, ctx.pwd, "sale.order", "search_read",
        [[["state", "in", ["sale", "done"]]]],
        {"fields": ["name", "partner_id", "amount_total", "date_order", "state"],
         "limit": limit, "order": "date_order desc"})
```

Add sibling handlers for `/purchase`, `/crm`, `/stock`, `/pos`, `/kpis` (aggregate for the
dashboard tiles). Keep them **read-only** in v1; writes come in a later phase behind stricter auth.

### 3.3 Auth mapping (`auth.py`)

`koma-spa` authenticates staff via **Auth0** (email + TOTP) or **Keycloak X.509 smart-card**. The
sidecar validates that token (as the other sidecars do), then maps to an Odoo identity. Two options:

1. **Service account (simplest, v1):** the sidecar holds one Odoo technical user's credentials and
   acts on its behalf; koma-spa RBAC decides who may call which endpoint. Fast to ship; the audit
   trail in Odoo shows the service user.
2. **Per-user Odoo accounts (v2):** provision an `res.users` per staff member (login = koma-spa
   email), map the validated token → that uid so Odoo's own record rules & audit apply. Better
   governance; needs a provisioning job. Recommended once payroll (sensitive) goes live.

---

## 4. Phase C — the Gabon payroll engine (from the PDF)

Pure python, **no Odoo import**, fully unit-testable. This is the heart of the "new features".

### 4.1 Rates & scale (`payroll/rates.py`) — transcribed from the PDF

```python
# --- Cotisations sociales (source: PDF pp.4-9) ---
CNSS_EMPLOYEE   = 0.025    # 2.5 %
CNSS_EMPLOYER   = 0.201    # 20.10 %
CNSS_CEILING    = 1_500_000  # FCFA / mois
CNAMGS_EMPLOYEE = 0.02     # 2.0 %  (no ceiling)
CNAMGS_EMPLOYER = 0.041    # 4.10 %
FNH_EMPLOYER    = 0.02     # 2.0 %  (employer only)

# --- TCS (Taxe Complémentaire sur les Salaires) ---
TCS_ALLOWANCE = 150_000    # abattement exonéré / mois
TCS_RATE      = 0.05       # 5 % sur le surplus

# --- IRPP ---
IRPP_PRO_ALLOWANCE      = 0.20        # abattement forfaitaire frais pro
IRPP_PRO_ALLOWANCE_CAP  = 833_333     # plafond mensuel de l'abattement
# Barème mensuel PAR PART (borne_haute, taux) — la dernière borne est None (au-delà)
IRPP_BRACKETS = [
    (125_000,   0.00),
    (250_000,   0.05),
    (500_000,   0.15),
    (1_250_000, 0.20),
    (2_500_000, 0.25),
    (None,      0.35),
]
```

### 4.2 Engine (`payroll/gabon.py`)

```python
from dataclasses import dataclass
from . import rates as R


@dataclass
class PayInput:
    basic: float            # salaire de base
    primes_imposables: float = 0.0   # gardes de nuit, astreintes, majorations
    avantages_nature: float = 0.0    # logement/véhicule (réintégrés)
    parts: float = 1.0               # quotient familial


@dataclass
class Payslip:
    brut_imposable: float
    cnss_sal: float
    cnamgs_sal: float
    tcs_sal: float
    irpp: float
    net_a_payer: float
    cnss_pat: float
    cnamgs_pat: float
    fnh_pat: float
    charges_patronales: float
    cout_employeur: float


def _irpp_per_part(base_per_part: float) -> float:
    tax, lower = 0.0, 0.0
    for upper, rate in R.IRPP_BRACKETS:
        span = (base_per_part - lower) if upper is None else min(base_per_part, upper) - lower
        if span > 0:
            tax += span * rate
        if upper is not None and base_per_part <= upper:
            break
        if upper is not None:
            lower = upper
    return tax


def compute(inp: PayInput) -> Payslip:
    brut = inp.basic + inp.primes_imposables + inp.avantages_nature

    # 1. Cotisations salariales
    cnss_sal = min(brut, R.CNSS_CEILING) * R.CNSS_EMPLOYEE
    cnamgs_sal = brut * R.CNAMGS_EMPLOYEE

    # 2. TCS : base = (brut - CNSS_sal), abattement 150 000, 5 % du surplus
    tcs_base = brut - cnss_sal
    tcs_sal = max(0.0, (tcs_base - R.TCS_ALLOWANCE) * R.TCS_RATE)

    # 3. IRPP : base = (brut - CNSS_sal) - TCS_sal, abattement pro 20 % (plafonné),
    #           quotient familial, barème progressif par part
    irpp_base = (brut - cnss_sal) - tcs_sal
    pro = min(irpp_base * R.IRPP_PRO_ALLOWANCE, R.IRPP_PRO_ALLOWANCE_CAP)
    net_imposable = irpp_base - pro
    per_part = net_imposable / inp.parts if inp.parts else net_imposable
    irpp = _irpp_per_part(per_part) * inp.parts

    net = brut - cnss_sal - cnamgs_sal - tcs_sal - irpp

    # 4. Charges patronales
    cnss_pat = min(brut, R.CNSS_CEILING) * R.CNSS_EMPLOYER
    cnamgs_pat = brut * R.CNAMGS_EMPLOYER
    fnh_pat = brut * R.FNH_EMPLOYER
    charges_pat = cnss_pat + cnamgs_pat + fnh_pat

    return Payslip(
        brut_imposable=round(brut), cnss_sal=round(cnss_sal), cnamgs_sal=round(cnamgs_sal),
        tcs_sal=round(tcs_sal), irpp=round(irpp), net_a_payer=round(net),
        cnss_pat=round(cnss_pat), cnamgs_pat=round(cnamgs_pat), fnh_pat=round(fnh_pat),
        charges_patronales=round(charges_pat), cout_employeur=round(brut + charges_pat))
```

### 4.3 Validation test vector (`tests/test_gabon_payroll.py`)

Worked from the PDF's formulas — a soignant on 800 000 FCFA brut imposable, 1 part:

| Ligne | Formule | Montant (FCFA) |
|---|---|---|
| Brut imposable | 800 000 | **800 000** |
| CNSS salariale | min(800 000, 1 500 000) × 2,5 % | 20 000 |
| CNAMGS salariale | 800 000 × 2,0 % | 16 000 |
| TCS salariale | max(0, (800 000 − 20 000 − 150 000) × 5 %) | 31 500 |
| IRPP | barème par part sur base 598 800 | 63 510 |
| **Net à payer** | 800 000 − 20 000 − 16 000 − 31 500 − 63 510 | **668 990** |
| CNSS patronale | 800 000 × 20,10 % | 160 800 |
| CNAMGS patronale | 800 000 × 4,10 % | 32 800 |
| FNH patronale | 800 000 × 2,0 % | 16 000 |
| **Coût employeur** | 800 000 + 209 600 | **1 009 600** |

```python
from app.payroll.gabon import PayInput, compute

def test_soignant_800k_one_part():
    p = compute(PayInput(basic=800_000, parts=1.0))
    assert p.cnss_sal == 20_000
    assert p.cnamgs_sal == 16_000
    assert p.tcs_sal == 31_500
    assert p.irpp == 63_510
    assert p.net_a_payer == 668_990
    assert p.cout_employeur == 1_009_600
```

> **Interpretation points to confirm with the local expert** (the PDF is slightly ambiguous):
> the exact IRPP base ordering (whether the 20 % pro-allowance applies before or after the family
> quotient), whether `avantages en nature` enter CNSS as well as IRPP/CNAMGS, and the precise
> definition of "brut imposable" vs "brut". The engine centralises all of this in `rates.py` +
> `gabon.py`, so a rule change is a one-file edit + a re-run of the test vector.

### 4.4 Payroll endpoints (`routers/paie.py`)

```python
@router.post("/simulate")            # live payslip preview (no persistence)
async def simulate(inp: PayInput): return compute(inp)

@router.post("/run/{employee_id}")   # pulls contract+attendance from Odoo, computes, stores back
async def run(employee_id: int, period: str, ctx=Depends(odoo_ctx)):
    emp = await ctx.rpc.execute_kw(ctx.uid, ctx.pwd, "hr.employee", "read",
        [[employee_id]], {"fields": ["x_parts_irpp", "x_cnss", "x_cnamgs"]})
    contract = ...   # hr.contract wage; hr.attendance → primes gardes
    slip = compute(PayInput(basic=..., primes_imposables=..., parts=emp[0]["x_parts_irpp"]))
    # persist as an account.move (journal entry) or a custom x_bulletin model — see Phase E
    return slip
```

---

## 5. Phase D — the PWA frontend inside `koma-spa` ✅ (scaffolded)

### 5.1 Route & page — one tabbed page, not three

The guide originally sketched three routes (`/staff/erp`, `/staff/hr`, `/staff/paie`). In
implementation they **collapsed into a single tabbed page** — the same idiom as `GeoppsPage`
(react-bootstrap `Tab.Container`) — which is cleaner and needs only one route + one RBAC key:

| Route | Page | Tabs | Data source |
|---|---|---|---|
| `/staff/erp` | `src/pages/ErpPage.jsx` | **Tableau de bord · RH · Paie (Gabon)** | `GET {ODOO}/erp/*`, `/hr/*`, `POST /paie/simulate` |

Wiring done (files touched):
- **`src/pages/ErpPage.jsx`** — new page. KPI tiles + recent SO/PO tables (ERP tab), employee table
  with the `l10n_ga_hr` fields (RH tab), and the payroll simulator (Paie tab, gated to admin/manager).
- **`src/App.jsx`** — `import ErpPage`; route
  `<Route path="/staff/erp" element={<AuthGuard><RoleGuard feature="erp"><ErpPage/></RoleGuard></AuthGuard>}/>`;
  breadcrumb-title map entry `'/staff/erp': 'staffErp'`.
- **`src/data/staffRoles.js`** — added feature key `'erp'` to `manager` (admin has `'*'`); `RoleGuard`
  + the `/staff` tile filter both honour it.
- **`src/pages/StaffPage.jsx`** — `Boxes` icon import + a `SHORTCUTS` tile → `/staff/erp`.
- **i18n** — `staff.shortcuts.erp` / `erpDesc` + breadcrumb title `staffErp` added to
  `fr/en/es/de.js`; in-page copy is French-first via inline `t(key, 'français par défaut')`.
- **`.env.example`** — `VITE_ODOO_URL=http://localhost:8030`.

Conventions honoured: reads go through **`jsonFetch` + `actorHeaders(user, role)`** (the same
`X-Actor-*` dev-stub headers every sidecar understands — so the Principal the sidecar sees matches
koma-spa's RBAC); **XAF/FCFA** via `Intl.NumberFormat('fr-FR', {currency:'XAF'})`; a **"service hors
ligne"** offline note when `odoo-service` is unreachable.

> **Port note:** `odoo-service` runs on **8030**, not 8028 — 8028 is already `tenant-service`
> (`VITE_TENANT_URL`) and 8029 is `scheduling-service`. 8030 is the next free sidecar port.

### 5.2 The PWA layer — already configured, just extended

Unlike the guide's original assumption, **koma-spa already ships a full PWA** (`vite-plugin-pwa` in
`vite.config.js`: manifest, Workbox service worker, `registerType: 'autoUpdate'`, precache + runtime
caching). There is **no new manifest to add** — the app installs and runs offline today under one
app identity (`id: '/'`). Phase D only adds one runtime-cache rule for the sidecar:

```js
// vite.config.js → VitePWA workbox.runtimeCaching[] (added first)
{
  // odoo-service (ERP/HR reads) — different origin, GET only. Workbox never
  // caches POST, so payroll runs (/paie) stay online-only automatically.
  urlPattern: ({ url, request }) =>
    request.method === 'GET' &&
    url.origin !== self.location.origin &&
    /^\/(erp|hr)\//.test(url.pathname),
  handler: 'NetworkFirst',
  options: { cacheName: 'odoo-api', networkTimeoutSeconds: 5,
             expiration: { maxEntries: 60, maxAgeSeconds: 60 * 60 * 24 } },
}
```

- **App shell** (React bundle, routes, icons) is already precached → installs to home screen,
  launches offline.
- **ERP/HR reads** → *NetworkFirst*: latest when online, last-known snapshot offline (read-only).
- **Payroll `/paie/*`** is POST → Workbox ignores it → **online-only by construction**, no stale
  bulletins. (The pattern also excludes `/paie` from the path regex for good measure.)
- Verified: `npm run lint` clean, `npm run build` green (`dist/sw.js` regenerated, 218 precache
  entries), and the sidecar answers on 8030 (`/health` → `odoo.reachable: true`, `/erp/kpis` live).

---

## 6. Phase E — persistence, security, deployment ✅ (scaffolded)

- **Where bulletins live — done.** Computed payslips persist as a new **`x.bulletin.paie`** model in
  the `l10n_ga_hr` addon (employee, période, inputs, all lines, `computed_by`, `computed_on`, and a
  `rates_snapshot` JSON). The snapshot pins the exact CNSS/CNAMGS/FNH/TCS/IRPP values used
  (tagged `RATES_VERSION`), so a bulletin recomputes identically after a future rate change. A
  **Paie Gabon → Bulletins de paie** menu + list/form views expose them in Odoo; ACLs grant
  `hr.group_hr_user` (read/write/create) and `hr.group_hr_manager` (+delete). Money fields are plain
  `Float` (FCFA) because the demo company runs in USD and XAF is inactive — Monetary would mis-render.
  Accounting posting is now done in **Phase F** (`/paie/post` → linked `move_id`).
- **Sidecar `/paie/run` — done.** Computes from the employee's Odoo wage (`?basic=` override
  supported), **persists** the `x.bulletin.paie` record, stamps the caller's identity, and writes an
  **audit** line (`odoo-service.audit`: bulletin, employee, période, net, coût, by, rates version).
  `GET /paie/bulletins?employee_id=&period=` lists them. Writes are POST → never cached by the SW.
- **Compose wiring — done.** `eSante/odoo/docker-compose.yml` now defines the `odoo-service`:
  ```yaml
  odoo-service:
    build: ../koma-spa/odoo-service
    depends_on: { odoo: { condition: service_started } }
    ports: ["8030:8030"]
    environment:
      ODOO_URL: "http://odoo:8069"     # same compose network — Odoo stays off the public interface
      ODOO_DB: "odopk"
      ODOO_SERVICE_LOGIN: "admin"
      ODOO_SERVICE_PASSWORD: "admin"
      ODOO_AUTH_DISABLED: "true"        # dev; set false + Keycloak JWKS in prod
      CORS_ORIGINS: "http://localhost:5173,http://localhost:4173"
  ```
  `docker compose up -d` now brings up **db + odoo + odoo-service** together. A `.dockerignore`
  keeps the dev `.venv`/tests out of the build context. In prod, keep Odoo's 8069 **off the public
  interface** — only the sidecar and the DB manager should reach it.
- **Secrets.** Odoo service-account credentials and the DB master password go in env/secrets, never
  in the repo. The sidecar is the trust boundary — validate the koma-spa token on every request.
- **Payroll sensitivity.** Restrict `/paie/*` to an HR/finance role in koma-spa RBAC; log every run
  (who, when, which rates). Prefer per-user Odoo accounts (§3.3 option 2) before go-live so Odoo's
  own audit trail applies.
- **No test runner in koma-spa** (by design) — but the **sidecar has pytest**; make
  `test_gabon_payroll.py` + `test_attendance_premiums.py` a CI gate. It's the one place correctness
  is non-negotiable.

---

## 6b. Phase F — attendance premiums, accounting, per-user identity ✅ (scaffolded)

- **Attendance → premiums** (`app/payroll/attendance.py`, pure python, tested). Night hours
  (21 h–06 h, **+50 %**) and Sunday/holiday hours (**+100 %**) are tallied by slicing each
  check-in→check-out interval at clock-hour boundaries; the *majoration* portion becomes an imposable
  prime (`prime = hourly × majoration × hours`, `hourly = basic / 173.33`). Endpoint
  `GET /paie/attendance-premiums/{id}?period=AAAA-MM`; `POST /paie/run/{id}?auto_primes=true` fills
  `primes_imposables` from it automatically. Rules live in `rates.py` (`NIGHT_*`, `SUNDAY_MAJORATION`).
- **Accounting** — `POST /paie/post/{bulletin_id}` builds a **balanced draft `account.move`** mirroring
  the bulletin and links it via `x.bulletin.paie.move_id`. Journal (`type=general`) and accounts
  (`account_type` `expense` / `liability_current`) are resolved **at runtime within the caller's
  company** — no hard-coded codes (Odoo 19 account codes are company-scoped, not a plain column).
  Lines: Dr *Salaires + charges* = coût employeur; Cr *Net à payer* + Cr *Organismes sociaux & impôts*.
  Left in **draft** for an accountant to review and post.
- **Per-user provisioning** (`app/provisioning.py`) — `ensure_user(rpc, principal)` finds-or-creates a
  `res.users` (login = email, `base.group_user`) for the caller and returns its uid; `/paie/run`
  stamps it on `computed_by_uid`, giving per-person attribution now and a seam for full per-user RPC
  auth (v2) later. Best-effort: a provisioning failure never blocks a payroll run.
- **Verified end-to-end:** seeded night+Sunday attendances → premiums `2000 + 4000 = 6000`;
  `auto_primes` run by a fresh actor provisioned `res.users` uid=7 and stamped it on the bulletin;
  `/paie/post` produced a balanced move (Dr 226 314 = Cr 169 324 + 56 990), linked + audit-logged.
  `pytest` 10 passed.

---

## 7. Phased roadmap

| Phase | Deliverable | Exit criteria |
|---|---|---|
| **A** ✅ | HR modules + `l10n_ga_hr` addon installed in `odopk` | **Done** — `hr`, `hr_holidays`, `hr_attendance`, `hr_work_entry`, `hr_skills`, `hr_recruitment`, `project` + `l10n_ga_hr` installed; employees carry CNSS/CNAMGS/parts via the "Paie (Gabon)" tab; gardes tracked via attendance |
| **B** | `odoo-service` sidecar, read-through ERP endpoints | `/staff/erp` shows live Sales/Stock/Purchase/CRM/POS tiles |
| **C** | Gabon payroll engine + `/paie/simulate` | Test vector (§4.3) green; `/staff/paie` simulator works |
| **D** ✅ | `/staff/erp` tabbed page + sidecar cache rule | **Done** — page (ERP/RH/Paie tabs) wired into routes + RBAC + `/staff` tile + i18n (fr/en/es/de); PWA already existed, added NetworkFirst rule for `odoo-service` GET reads; lint + build green |
| **E** ✅ | Payroll persistence + audit + compose wiring | **Done** — `x.bulletin.paie` model (menu/views/ACLs) stores every run with `computed_by` + `rates_snapshot`; `/paie/run` persists + audits, `/paie/bulletins` lists; `docker compose up` starts db+odoo+odoo-service together. *Accounting `account.move` posting deferred to F.* |
| **F** ✅ | Attendance premiums · accounting · per-user provisioning | **Done** — attendance→premiums engine (night +50 %, dimanche/férié +100 %) auto-fills `/paie/run?auto_primes=true`; `/paie/post` creates a balanced draft `account.move` linked via `move_id`; `ensure_user` provisions a `res.users` per caller and stamps `computed_by_uid` for per-person audit |

---

## 8. Source mapping (PDF → this guide)

| PDF element | Where it lands |
|---|---|
| Tool comparison (ERPNext / Odoo / OrangeHRM / Dolibarr) | Decision: **Odoo Community** (already deployed); payroll gap filled by sidecar, not ERPNext |
| Gabon CNSS/CNAMGS/FNH rates, ceiling | `payroll/rates.py` §4.1 |
| TCS base + 150 000 abattement + 5 % | `compute()` TCS block §4.2 |
| IRPP: 20 % pro-allowance (cap 833 333), quotient familial, 6-bracket scale | `_irpp_per_part()` + `IRPP_BRACKETS` §4.1–4.2 |
| Odoo salary-rule Python (`min(categories.GROSS,1500000)*0.025`, …) | Re-expressed as tested python in the sidecar §4.2 (Odoo Community has **no** payroll module here) |
| Custom fields `x_cnss`, `x_cnamgs`, `x_parts_irpp` | `l10n_ga_hr` addon §2.1 |
| Modules `hr`, `hr_holidays`, `hr_attendance` | Phase A install §2 (note: `hr_payroll`/`om_hr_payroll` **not available** — see §0) |
| Gardes/astreintes, majorations nuit/férié, avantages en nature | `PayInput.primes_imposables` / `avantages_nature` §4.2; attendance feed §4.4 |
| Medical planning 24/7, 60 staff | Attendance + work-entry (Phase A); planning helpers in `l10n_ga_hr` |

---

### Appendix — quick commands

```bash
# Odoo (from eSante/odoo)
docker compose up -d                     # start Odoo + Postgres
docker compose logs -f odoo              # follow logs
docker compose stop odoo                 # before any -i/-u module op

# Install HR + Gabon addon
MSYS_NO_PATHCONV=1 docker compose run --rm odoo \
  odoo -c /etc/odoo/odoo.conf -d odopk --with-demo \
  -i hr,hr_holidays,hr_attendance,hr_work_entry,l10n_ga_hr --stop-after-init

# Sidecar (from koma-spa/odoo-service)
uvicorn app.main:app --reload --port 8030
pytest tests/ -q                         # payroll correctness gate

# Frontend (from koma-spa)
npm run dev                              # http://localhost:5173  (set VITE_ODOO_URL=http://localhost:8030)
npm run build                            # → dist/ (includes service worker)
```
