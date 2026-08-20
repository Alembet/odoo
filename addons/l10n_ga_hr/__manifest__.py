{
    "name": "Gabon HR Localisation (Polyclinique Koma)",
    "version": "19.0.3.0.0",
    "summary": "Champs RH gabonais (CNSS, CNAMGS, parts IRPP) et repères paie pour la clinique",
    "description": """
Localisation RH Gabon pour la Polyclinique Koma
================================================
Ajoute au dossier employé les identifiants et paramètres nécessaires au calcul
de paie gabonais (CNSS, CNAMGS, quotient familial IRPP) et un marqueur pour le
personnel soignant soumis aux gardes 24/7.

Le moteur de calcul de paie lui-même vit dans le sidecar `odoo-service`
(voir odoo-pwa-implementation-guide.md) : ce module ne fournit que les données,
pas le calcul.
""",
    "author": "Getic X / Polyclinique Koma",
    "website": "https://koma-ga.com",
    "license": "LGPL-3",
    "category": "Human Resources/Localization",
    "depends": ["hr", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_employee_views.xml",
        "views/bulletin_paie_views.xml",
    ],
    "installable": True,
    "application": False,
}
