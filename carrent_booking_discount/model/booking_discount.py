from openerp import models, fields, api, netsvc
from openerp.tools import misc, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, ValidationError
from decimal import Decimal
from ..text import WARN_HEAD1, WARN_DEFAULT_COMPANY, WARN_HEAD2, WARN_PRICE_OVERLAP
import datetime
import time
import urllib2


class discount_setting(models.Model):
	_name = "dtbs.carrent.booking.discount.setting"
	_description = "Discount Setting"


	name = fields.Char(string="Discount Name", required=True)
	isactive = fields.Boolean(string="Active", default=False)
	currency_id = fields.Many2one(comodel_name="res.currency", string="Currency", required=True, default=lambda self: self._get_default_currency())
	company_id = fields.Many2one(comodel_name="res.company", string="Company", default=lambda self: self._get_default_company())
	customer_id = fields.Many2one(comodel_name="res.partner", string="Customer", domain=[("customer", "=", True)])
	discount_line = fields.One2many(comodel_name="dtbs.carrent.discount.line.setting", inverse_name="discount_id", string="Discount Lines")



	@api.model
	def _get_default_company(self):
		company_id = self.env['res.users']._get_company()
		if not company_id:
			raise except_orm(WARN_HEAD1, WARN_DEFAULT_COMPANY)
		return company_id

	@api.model
	def _get_default_currency(self):
		comp = self.env['res.users'].browse().company_id
		if not comp:
			comp_id = self.env['res.company'].search([]).id
			comp = self.env['res.company'].browse(comp_id)
		return comp.currency_id.id


class discount_line_setting(models.Model):
	_name = "dtbs.carrent.discount.line.setting"
	_description = "Discount Line Setting"


	discount_id = fields.Many2one(comodel_name="dtbs.carrent.booking.discount.setting", string="Discount", required=True)
	unit_model = fields.Many2one(comodel_name="dtbs.carrent.model", string="Unit Model")
	date_start = fields.Date(string="Start Date")
	date_end = fields.Date(string="End Date")
	persentage = fields.Float(string="Discount (%)", required=True, default=lambda self: 0.0)


	@api.constrains('discount_id', 'date_start', 'date_end')
	def constraint_date(self):
		for pricelist_version in self:
			where = []
			if pricelist_version.date_start:
				where.append("((date_end>='%s') or (date_end is null))" % (pricelist_version.date_start,))
			if pricelist_version.date_end:
				where.append("((date_start<='%s') or (date_start is null))" % (pricelist_version.date_end,))

			self._cr.execute('SELECT id ' \
					'FROM dtbs_carrent_discount_line_setting ' \
					'WHERE '+' and '.join(where) + (where and ' and ' or '')+
						'discount_id = %s ' \
						'AND id <> %s', (
							pricelist_version.discount_id.id,
							pricelist_version.id))
			if self._cr.fetchall():
				raise Warning(WARN_HEAD2, WARN_PRICE_OVERLAP)
		return True


class booking(models.Model):
	_inherit = 'dtbs.carrent.booking'

	discount_id = fields.Many2one(comodel_name='dtbs.carrent.booking.discount.setting', string="Discount", readonly=True, states={'draft': [('readonly', False)]})
	persentage = fields.Float(compute="_get_persetage_discount", string="Discount (%)", store=True)

	@api.depends('discount_id', 'date_order', 'unit_id')
	def _get_persetage_discount(self):
		discount_line_obj = self.env['dtbs.carrent.discount.line.setting']
		discount_line_ids = discount_line_obj.search([
				'|', '|', '|', '&', ('unit_model','=', False),
				'&', '&', ('discount_id','=',self.discount_id.id), ('date_start','<=', self.date_order), ('date_end','>=', self.date_order),
				'&', '&', ('discount_id','=',self.discount_id.id), ('date_start','=', False), ('date_end','>=', self.date_order),
				'&', '&', ('discount_id','=',self.discount_id.id), ('date_start','<=', self.date_order), ('date_end','=', False),
				'|', '|', '&', ('unit_model','=', self.unit_id.model_id.id),
				'&', '&', ('discount_id','=',self.discount_id.id), ('date_start','<=', self.date_order), ('date_end','>=', self.date_order),
				'&', '&', ('discount_id','=',self.discount_id.id), ('date_start','=', False), ('date_end','>=', self.date_order),
				'&', '&', ('discount_id','=',self.discount_id.id), ('date_start','<=', self.date_order), ('date_end','=', False)
			])
		for disc in discount_line_ids:
			self.persentage = disc.persentage


	@api.model
	def get_group_discount_per_so_line(self):
		group_discount = self.env['ir.model.data'].get_object('sale', 'group_discount_per_so_line')
		res = [user for user in group_discount.users]
		return len(res) and True or False


	@api.multi
	def create_order(self):
		res = super(booking, self).create_order()

		if 'order_line' not in res:
			res['order_line'] = {}

		x = self.get_group_discount_per_so_line()
		if x:
			res['order_line'].update({
				'discount': self.persentage
				})

		return res


# =========  Sale Order Line Inherit =========== #
class sale_order_line(models.Model):
	_inherit = 'sale.order.line'


	@api.model
	def get_group_discount_per_so_line(self):
		group_discount = self.env['ir.model.data'].get_object('sale', 'group_discount_per_so_line')
		res = [user for user in group_discount.users]
		return len(res) and True or False

	@api.multi
	def booking_no_change(self, book_no, partner_id=False):
		res = super(sale_order_line, self).booking_no_change(book_no, partner_id=partner_id)


		if book_no:
			booking_obj = self.env['dtbs.carrent.booking']
			booking_obj = booking_obj.browse(book_no)

			if 'value' not in res:
				res['value'] = {}

			x = self.get_group_discount_per_so_line()

			if x:
				res['value'].update({
					'discount':booking_obj.persentage
					})
		return res