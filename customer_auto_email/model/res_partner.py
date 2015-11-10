from openerp.osv import osv, fields

class res_partner(osv.osv):
	_inherit = 'res.partner'
	_columns = {}

	def create(self, cr, uid, vals, context=None):
		res = super(res_partner, self).create(cr, uid, vals, context=context)

		config = self.pool.get("ir.model.data").xmlid_to_object(cr, uid, "customer_auto_email.configuration")


		if (config.default_auto_mail == True):
			if vals:
				template = self.pool.get('ir.model.data').get_object(cr, uid, 'customer_auto_email', 'email_template_customer_auto')
				mail_id = self.pool.get('email.template').send_mail(cr, uid, template.id, res , force_send=True)

		return res

res_partner()