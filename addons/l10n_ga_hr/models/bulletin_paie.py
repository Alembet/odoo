from odoo import api, fields, models


class BulletinPaie(models.Model):
    """Gabon payslip record — computed by the odoo-service sidecar and stored
    back here so every bulletin is auditable and reproducible.

    Money fields are plain Float in FCFA (XAF): the demo company runs in USD and
    XAF is inactive, so Monetary would render in the wrong currency. The
    `rates_snapshot` JSON captures exactly which CNSS/CNAMGS/FNH/TCS/IRPP values
    produced these numbers, so a bulletin can be recomputed identically later
    even after the rates change.
    """

    _name = "x.bulletin.paie"
    _description = "Bulletin de paie (Gabon)"
    _order = "period desc, employee_id"
    _rec_name = "name"

    name = fields.Char(string="Référence", default="/", copy=False, readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Employé", required=True,
                                  ondelete="cascade", index=True)
    period = fields.Char(string="Période (AAAA-MM)", required=True, index=True)
    state = fields.Selection(
        [("draft", "Brouillon"), ("confirmed", "Confirmé")],
        string="État", default="draft", required=True)

    # Inputs
    parts = fields.Float(string="Parts IRPP", default=1.0)
    basic = fields.Float(string="Salaire de base")
    primes_imposables = fields.Float(string="Primes imposables")
    avantages_nature = fields.Float(string="Avantages en nature")

    # Computed payslip lines (FCFA)
    brut_imposable = fields.Float(string="Brut imposable")
    cnss_sal = fields.Float(string="CNSS salariale")
    cnamgs_sal = fields.Float(string="CNAMGS salariale")
    tcs_sal = fields.Float(string="TCS salariale")
    irpp = fields.Float(string="IRPP")
    net_a_payer = fields.Float(string="Net à payer")
    cnss_pat = fields.Float(string="CNSS patronale")
    cnamgs_pat = fields.Float(string="CNAMGS patronale")
    fnh_pat = fields.Float(string="FNH patronale")
    charges_patronales = fields.Float(string="Total charges patronales")
    cout_employeur = fields.Float(string="Coût employeur")

    # Audit / reproducibility
    computed_by = fields.Char(string="Calculé par", help="Identité koma-spa ayant lancé le calcul.")
    computed_by_uid = fields.Many2one("res.users", string="Utilisateur Odoo",
                                      help="Compte Odoo provisionné pour l'auteur (audit par utilisateur).")
    computed_on = fields.Datetime(string="Calculé le", default=fields.Datetime.now)
    rates_snapshot = fields.Text(string="Barèmes utilisés (JSON)",
                                 help="Instantané des taux CNSS/CNAMGS/FNH/TCS/IRPP au moment du calcul.")

    # Accounting (Phase F) — the draft journal entry mirroring this bulletin.
    move_id = fields.Many2one("account.move", string="Écriture comptable", readonly=True,
                              copy=False, ondelete="set null")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                emp = vals.get("employee_id")
                period = vals.get("period", "")
                vals["name"] = f"PAIE/{period}/{emp}"
        return super().create(vals_list)
