""" Usage : Inherit the model res company and added and manage the functionality of Onboarding Panel"""
from odoo import fields, models, api

SHOPIFY_ONBOARDING_STATES = [('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done"),
                             ('closed', "Closed")]


class ResCompany(models.Model):
    
    _inherit = 'res.company'

    # Shopify Onboarding Panel
    shopify_onboarding_state = fields.Selection(selection=SHOPIFY_ONBOARDING_STATES,
                                                string="State of the shopify onboarding panel", default='not_done')
    shopify_instance_onboarding_state = fields.Selection(selection=SHOPIFY_ONBOARDING_STATES,
                                                         string="State of the shopify instance onboarding panel",
                                                         default='not_done')
    shopify_basic_configuration_onboarding_state = fields.Selection(SHOPIFY_ONBOARDING_STATES, default='not_done',
                                                                    string="State of the shopify basic configuration "
                                                                           "onboarding step")
    shopify_financial_status_onboarding_state = fields.Selection(SHOPIFY_ONBOARDING_STATES, default='not_done',
                                                                 string="State of the onboarding shopify financial "
                                                                        "status step")
    shopify_cron_configuration_onboarding_state = fields.Selection(SHOPIFY_ONBOARDING_STATES, default='not_done',
                                                                   string="State of the onboarding shopify cron "
                                                                          "configurations step")
    is_create_shopify_more_instance = fields.Boolean(string='Is create shopify more instance?', default=False)
    shopify_onboarding_toggle_state = fields.Selection(selection=[('open', "Open"), ('closed', "Closed")],
                                                       default='open')

    @api.model
    def action_close_shopify_instances_onboarding_panel(self):
        """ Mark the onboarding panel as closed. """
        self.env.company.shopify_onboarding_state = 'closed'

    def get_and_update_shopify_instances_onboarding_state(self):
       
        steps = [
            'shopify_instance_onboarding_state',
            'shopify_basic_configuration_onboarding_state',
            'shopify_financial_status_onboarding_state',
            'shopify_cron_configuration_onboarding_state',
        ]
        return self._get_and_update_onboarding_state('shopify_onboarding_state', steps)

    def action_toggle_shopify_instances_onboarding_panel(self):
       
        self.shopify_onboarding_toggle_state = 'closed' if self.shopify_onboarding_toggle_state == 'open' else 'open'
        return self.shopify_onboarding_toggle_state
