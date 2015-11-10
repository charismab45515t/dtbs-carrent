from openerp import models, fields, api

class ConfigData(models.Model):
    _name = "dtbs.automail.configuration.data"

    default_auto_mail = fields.Boolean("Allow Send Mail Automatically to New Customer", default=False)


class Configuration(models.TransientModel):
    _name = "dtbs.automail.settings"
    _inherit = "res.config.settings"

    default_auto_mail = fields.Boolean("Allow Send Mail Automatically to New Customer", default=False)

    @api.multi
    def set_default_automail_value(self):
        config = self.env["ir.model.data"].xmlid_to_object("customer_auto_email.configuration")
        config.write({
            "default_auto_mail": self.default_auto_mail
    })

    @api.multi
    def get_default_automail_value(self):
        config = self.env["ir.model.data"].xmlid_to_object("customer_auto_email.configuration")

        return {
            "default_auto_mail": config.default_auto_mail
        }
