from openerp import models, fields, api, _, netsvc
from openerp.tools import misc, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, ValidationError
from decimal import Decimal
import datetime
import time
import urllib2


# ============ Product Inherit ==============#
 
class product_template(models.Model):
	_inherit = "product.template"

	ischarge = fields.Boolean('Is Charge', default=False)


class charge_setting(models.Model):
	_name = "dtbs.carrent.booking.charge.setting"
	_rec_name = "product_id"
	_description = "Charge Setting"

	product_id = fields.Many2one(comodel_name='product.template', string='Product_id', required=True, delegate=True, ondelete='cascade')



class booking_charge(models.Model):

	@api.model
	def _needaction_count(self, domain=None):
		"""
		Show a count of draft state folio on the menu badge.
		@param self: object pointer
		"""
		return self.search_count([('state', '=', 'draft')])


	_name = "dtbs.carrent.booking.charge"
	_description = "Booking Charge"
	_rec_name = "no_fak"
	_inherit = ['ir.needaction_mixin']
	_order = 'id desc'



	no_fak = fields.Char(string="Charge Number", readonly=True)
	customer_id = fields.Many2one(comodel_name="res.partner", string="Customer", required=True, domain=[("customer", "=", True)], readonly=True, states={'draft': [('readonly', False)]})
	booking_id = fields.Many2one(comodel_name="dtbs.carrent.booking", string="Booking Number", required=True, readonly=True, states={'draft': [('readonly', False)]})
	date_end = fields.Date(string="Estimated Date End", required=True, readonly=True, states={'draft': [('readonly', False)]})
	real_date_end = fields.Date(string="Real Returned Date", required=True, readonly=True, states={'draft': [('readonly', False)]})
	late = fields.Integer(string="Time (day)", required=True)
	state = fields.Selection([('draft', 'Draft'),('invoic', 'Invoiced'),('except', 'Exception')], string='Status', default='draft')
	company_id = fields.Many2one(comodel_name='res.company', string='Company', states={'draft': [('readonly', False)]}, default=lambda self: self._get_default_company())
	comment = fields.Text(string="Additional Information")
	invoice_id = fields.Many2one(comodel_name="account.invoice", string="Invoice", auto_join=True)


	@api.model
	def _get_default_company(self):
		company_id = self.env['res.users']._get_company()
		if not company_id:
			raise except_orm('Error!', 'There is no default company for the current user!')
		return company_id


	@api.onchange('date_end','real_date_end')
	def onchange_date(self):
		if self.date_end and self.real_date_end:
			d_end = datetime.datetime.strptime(self.date_end, DEFAULT_SERVER_DATE_FORMAT)
			d_real_end = datetime.datetime.strptime(self.real_date_end, DEFAULT_SERVER_DATE_FORMAT)
			daysDiff = str((d_real_end-d_end).days)

			self.late = daysDiff
		else:
			self.late = 0


	@api.model
	def create_new_invoice(self):
		journal_ids = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.company_id.id)],
			limit=1)
		if not journal_ids:
			raise Warning(('Error!'),('Please define sales journal for this company: "%s" (id:%d).') % (self.company_id.name, self.company_id.id))

		product_ids = self.env['dtbs.carrent.booking.charge.setting'].search([('ischarge','=',True)])

		invoice_line = {
			'product_id': product_ids.product_id.id,
			'name': product_ids.name,
			'quantity': self.late,
			'uos_id': product_ids.uom_id.id,
			'price_unit': product_ids.list_price
		}

		invoice_vals = {
			'name': '',
			'origin': self.no_fak,
			'type': 'out_invoice',
			'reference': self.booking_id.no_book or self.no_fak,
			'account_id': self.customer_id.property_account_receivable.id,
			'partner_id': self.booking_id.partner_invoice_id.id,
			'journal_id': journal_ids.id,
			'invoice_line': [(0, 0, invoice_line)],
			'currency_id': self.booking_id.sale_price_currency_id.id,
			'comment': self.comment,
			'payment_term': self.booking_id.sales_order_id.payment_term and self.booking_id.sales_order_id.payment_term.id or False,
			'fiscal_position': self.booking_id.sales_order_id.fiscal_position.id or self.booking_id.sales_order_id.partner_id.property_account_position.id,
			'date_invoice': self._context.get('date_invoice', False),
			'company_id': self.company_id.id,
			'user_id': self.booking_id.sales_order_id.user_id and self.booking_id.sales_order_id.user_id.id or False,
			'section_id' : self.booking_id.sales_order_id.section_id.id
		}

		invoice_obj = self.env['account.invoice']
		res = invoice_obj.create(invoice_vals)
		invoice_obj.button_compute([res])
		return res


	@api.multi
	def recreate_invoice(self):
		inv_id = self.create_new_invoice()
		self.write({'invoice_id': inv_id.id})
		return True


	@api.multi
	def invoiced_charge(self):
		inv_id = self.create_new_invoice()
		self.write({'state': 'invoic', 'invoice_id': inv_id.id})
		return True


	@api.multi
	def exception_charge(self):
		self.write({'state': 'except'})
		return True


	@api.model
	def create(self, vals):
		# auto number
		if vals.get('no_fak','/')=='/':
			vals['no_fak'] = self.env['ir.sequence'].get('dtbs.carrent.booking.charge') or '/'
		context = dict({}, mail_create_nolog=True)
		fak =  super(booking_charge, self).create(vals)
		return fak


# ============ Return Wizard Inherit ==============#
class booking_return_wizard(models.TransientModel):
	_inherit = "dtbs.carrent.return.wizard"

	@api.one
	def return_unit(self):
		res = super(booking_return_wizard, self).return_unit()

		active_id = self._context['active_id']
		booking = self.env['dtbs.carrent.booking'].browse(active_id)
		daysDiff = 0

		for record in booking:
			d_end = datetime.datetime.strptime(record.date_end, DEFAULT_SERVER_DATE_FORMAT)
			d_real_end = datetime.datetime.strptime(self.date_return, DEFAULT_SERVER_DATE_FORMAT)
			daysDiff = str((d_real_end-d_end).days)

			val = {
					'customer_id': record.customer_id.id,
					'booking_id': record.id,
					'date_end': record.date_end,
					'real_date_end': self.date_return,
					'late': daysDiff,
					'comment': 'Late fee rental'
					}
			self.env['dtbs.carrent.booking.charge'].create(val)


		return res