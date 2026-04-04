from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    food_kiosk_agent_url = fields.Char(
        string='Agent URL',
        config_parameter='food_kiosk.agent_url',
        default='https://agent.food.ecocupon.cl',
        help='URL of the payment agent (FastAPI service)'
    )
    food_kiosk_default_amount = fields.Float(
        string='Default Order Amount',
        config_parameter='food_kiosk.default_amount',
        default=9990.0,
        help='Default amount in CLP for kiosk orders'
    )
    food_kiosk_enabled = fields.Boolean(
        string='Enable Kiosk',
        config_parameter='food_kiosk.enabled',
        default=True,
    )
