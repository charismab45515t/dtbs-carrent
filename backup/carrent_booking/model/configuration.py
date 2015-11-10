from openerp import models, fields, api

class ConfigData(models.Model):
    _name = "dtbs.booking.configuration.data"

    default_auto_booking_mail = fields.Boolean("Allow Send Booking Mail Automatically to Customer", default=False)


class Configuration(models.TransientModel):
    _name = "dtbs.booking.settings"
    _inherit = "res.config.settings"

    default_auto_booking_mail = fields.Boolean("Allow Send Booking Mail Automatically to Customer", default=False)

    @api.multi
    def set_default_automail_booking_value(self):
        config = self.env["ir.model.data"].xmlid_to_object("carrent_booking.configuration")
        config.write({
            "default_auto_booking_mail": self.default_auto_booking_mail
    })

    @api.multi
    def get_default_automail_booking_value(self):
        config = self.env["ir.model.data"].xmlid_to_object("carrent_booking.configuration")

        return {
            "default_auto_booking_mail": config.default_auto_booking_mail
        }
