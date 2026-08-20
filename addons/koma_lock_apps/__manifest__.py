{
    "name": "Koma - Hide Apps Menu",
    "summary": "Hide the Apps store and lock module installation for Polyclinique Koma",
    "description": """
Hides the Apps and Settings > Technical > Apps menus so that regular users
(and even administrators, in normal non-developer mode) cannot install new
modules such as Website, CRM, etc.

Fully reversible: uninstall this module, or activate Developer Mode, and the
Apps menu reappears. No source files are modified.
""",
    "author": "Polyclinique Koma",
    "website": "https://koma-ga.com",
    "category": "Technical",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/hide_apps.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
