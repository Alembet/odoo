from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # --- Identifiants organismes sociaux gabonais ---
    x_cnss = fields.Char(
        string="N° CNSS",
        groups="hr.group_hr_user",
        help="Numéro d'immatriculation à la Caisse Nationale de Sécurité Sociale.",
    )
    x_cnamgs = fields.Char(
        string="N° CNAMGS",
        groups="hr.group_hr_user",
        help="Numéro d'assuré à la Caisse Nationale d'Assurance Maladie et de "
        "Garantie Sociale.",
    )

    # --- Paramètre fiscal : quotient familial IRPP ---
    x_parts_irpp = fields.Float(
        string="Parts IRPP (quotient familial)",
        default=1.0,
        groups="hr.group_hr_user",
        help="Nombre de parts pour le calcul de l'IRPP selon la situation "
        "matrimoniale et le nombre d'enfants à charge.",
    )

    # --- Marqueur planning gardes 24/7 ---
    x_is_soignant = fields.Boolean(
        string="Personnel soignant (gardes 24/7)",
        help="Coché pour le personnel médical/soignant soumis aux gardes, "
        "astreintes et majorations de nuit/jours fériés.",
    )
