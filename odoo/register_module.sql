-- Register ecocupon_login module in Odoo 19 database
-- Theme category already exists (id=68)

INSERT INTO ir_module_module (name, state, author, website, summary, shortdesc, category_id, license, application, auto_install, create_date, write_date)
SELECT 
    'ecocupon_login', 
    'uninstalled', 
    'SmarterOS', 
    'https://ecocupon.cl', 
    '{"en_US": "Smarter Dumper branding for Odoo login"}'::jsonb,
    '{"en_US": "EcoCupon Login Theme"}'::jsonb,
    68, 
    'LGPL-3', 
    false, 
    false, 
    NOW(), 
    NOW()
WHERE NOT EXISTS (SELECT 1 FROM ir_module_module WHERE name = 'ecocupon_login');

-- Verify
SELECT name, state FROM ir_module_module WHERE name = 'ecocupon_login';
