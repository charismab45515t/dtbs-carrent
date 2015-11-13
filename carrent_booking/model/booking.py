from openerp import models, fields, api, netsvc
from openerp.tools import misc, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, ValidationError
from decimal import Decimal
from ..text import DRAFT, CONFIRM, SALE, RENT, CANCEL, RETURN, ASSIGN, UNASSIGN
from ..text import UNIQ_NUMBER
from ..text import WARN_HEAD1, WARN_DATE_RENT, WARN_DATE_OVERLAP, WARN_HEAD2, WARN_DEFAULT_COMPANY, WARN_HEAD3, WARN_BOOKING_CHANGE
from ..text import WARN_HEAD4, WARN_TIME_PERIOD
import datetime
import time
import urllib2

STATE = [
	('draft', DRAFT),
	('confirm', CONFIRM),
	('sale', SALE),
	('rent', RENT),
	('cancel', CANCEL),
	('return', RETURN),
]

STATE2 = [
	('assigned', ASSIGN), 
	('unassigned', UNASSIGN),
]

# =========  Booking =========== #
class Booking(models.Model):
	_name = "dtbs.carrent.booking"
	_rec_name = "no_book"
	_description = "Booking"
	_inherit = ['mail.thread', 'ir.needaction_mixin']
	_mail_post_access = 'read'
	_track = {
		'state': {
			'carrent_booking.mt_booking_new': lambda self, cr, uid, obj, ctx=None: obj.state == 'draft',
			'carrent_booking.mt_booking_stage': lambda self, cr, uid, obj, ctx=None: obj.state != 'draft',
		},
	}
	_order = 'date_order desc, date_rent desc, id desc'

	no_book = fields.Char(string="Booking Number", readonly=True, track_visibility='onchange')
	state = fields.Selection(STATE, string='Status', default='draft',
								track_visibility='onchange')
	customer_id = fields.Many2one(comodel_name="res.partner", string="Customer", required=True, domain=[("customer", "=", True)], states={'draft': [('readonly', False)]},
									track_visibility='onchange')
	date_order = fields.Date('Date Ordered', required=True, readonly=True, states={'draft': [('readonly', False)]},
									default=(lambda *a:time.strftime(DEFAULT_SERVER_DATE_FORMAT)))
	date_rent = fields.Date('Date Rent', required=True, readonly=True, states={'draft': [('readonly', False)]},
									default=(lambda *a:time.strftime(DEFAULT_SERVER_DATE_FORMAT)), track_visibility='onchange')
	# warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Rental', readonly=True, required=True, default=1, states={'draft': [('readonly', False)]})
	company_id = fields.Many2one(comodel_name='res.company', string='Company', states={'draft': [('readonly', False)]}, default=lambda self: self._get_default_company())
	partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Invoice Address', readonly=True, states={'draft':[('readonly', False)]},
									help="Invoice address for current booking.")
	partner_order_id = fields.Many2one(comodel_name='res.partner', string='Ordering Contact', readonly=True, states={'draft':[('readonly', False)]},
									help="The name and address of the contact that requested the order or quotation.")
	partner_shipping_id = fields.Many2one(comodel_name='res.partner', string='Delivery Address', readonly=True, states={'draft':[('readonly', False)]},
									help="Delivery address for current booking.")
	unit_id = fields.Many2one(comodel_name="dtbs.carrent.unit", string="Unit", states={'draft':[('readonly', False)]}, required=True, track_visibility='onchange')
	police = fields.Char(compute="_get_police", string="Police Number", store=True)
	pricelist = fields.Many2one(comodel_name="product.uom.price", string="Price Segmentation", states={'draft':[('readonly', False)]}, required=True, track_visibility='onchange')
	price = fields.Float(compute="_get_price_uom", string="Price", store=True)
	sale_uom = fields.Many2one(comodel_name="product.uom", compute="_get_police", string="Unit of Measure", store=True)
	sale_price = fields.Float(compute="_get_police", string="Price", store=True)
	sale_price_currency_id = fields.Many2one(comodel_name="res.currency", compute="_get_police", string="Currency", store=True)
	price_by_uom = fields.Boolean(string="Price by UOM",default=lambda self: self._get_default_by_uom())
	auto_mail = fields.Boolean(string="Auto Mail",default=lambda self: self._get_default_auto_mail())
	estimation_time = fields.Float(string="Estimated Time(s)", default=1, required=True)
	time_selection = fields.Selection([('day', 'Day(s)'),('month', 'Month(s)'),('year', 'Year(s)')], string='In', default='day', required=True)
	date_end = fields.Date(string="Estimated Date End", compute="_calc_date_end", store=True)
	sales_order_id = fields.Many2one(comodel_name="sale.order", string="Sales Order", auto_join=True)
	quotation = fields.Boolean(string="Quotation", default=False)
	date_return = fields.Date(string='Date Return')



	_sql_constraints = [
		("Unique Number", "UNIQUE(company_id,no_book)", UNIQ_NUMBER),
	]

	@api.constrains('no_book', 'date_order', 'date_rent')
	def constraint_date_rent(self):
		if self.date_order and self.date_rent:
			if self.date_rent < self.date_order:
				raise except_orm(WARN_HEAD1, WARN_DATE_RENT)


	@api.constrains('date_rent', 'date_end', 'unit_id')
	def constraint_date_overlap(self):
		if self.date_rent and self.date_end and self.unit_id:
			item_ids = self.search([('date_end', '>=', self.date_rent), ('date_rent', '<=', self.date_end), ('unit_id','=', self.unit_id.id), ('state', 'not in', ['cancel','return']), ('id', '<>', self.id)])
			if item_ids:
				raise except_orm(WARN_HEAD1, WARN_DATE_OVERLAP)
		


	@api.onchange('customer_id')
	def onchange_customer_id(self):
		if not self.customer_id:
			self.partner_invoice_id = False
			self.partner_shipping_id = False
			self.partner_order_id = False
		else:
			addr = self.customer_id.address_get(['delivery', 'invoice', 'contact'])
			self.partner_invoice_id = addr['invoice']
			self.partner_order_id = addr['contact']
			self.partner_shipping_id = addr['delivery']

	@api.depends('unit_id')
	def _get_police(self):
		police_obj = self.env['dtbs.carrent.unit']
		police_ids = police_obj.search([('id', '=', self.unit_id.id)])
		for unit in police_ids:
			self.police = unit.police
			self.sale_uom = unit.uom_id.id
			self.sale_price = unit.list_price
			self.sale_price_currency_id = unit.sale_price_currency_id.id

	@api.depends('pricelist')
	def _get_price_uom(self):
		price_obj = self.env['product.uom.price']
		price_ids = price_obj.search([('id', '=', self.pricelist.id)])
		for price in price_ids:
			self.price = price.price

	@api.depends('date_rent','estimation_time','time_selection')
	def _calc_date_end(self):
		if self.time_selection=='day':
			x = datetime.timedelta(days=self.estimation_time)
		elif self.time_selection=='month':
			x = datetime.timedelta(days=30*self.estimation_time)
		elif self.time_selection=='year':
			x = datetime.timedelta(days=365*self.estimation_time)
		else:
			x = datetime.timedelta(days=self.estimation_time)

		dt_end = (datetime.datetime.strptime(self.date_rent,DEFAULT_SERVER_DATE_FORMAT) + x) - datetime.timedelta(days=1)
		self.date_end = dt_end.strftime(DEFAULT_SERVER_DATE_FORMAT)


	@api.model
	def _get_default_by_uom(self):
		group_uom = self.env['ir.model.data'].get_object('product', 'group_uom')
		res = [user for user in group_uom.users]
		return len(res) and True or False


	@api.model
	def _get_default_company(self):
		company_id = self.env['res.users']._get_company()
		if not company_id:
			raise except_orm(WARN_HEAD2, WARN_DEFAULT_COMPANY)
		return company_id


	@api.model
	def _get_default_auto_mail(self):
		auto_mail = False
		config_id = self.env['dtbs.booking.configuration.data']
		config_ids = config_id.search([])
		for cnf in config_ids:
			auto_mail = cnf.default_auto_booking_mail

		return auto_mail


	@api.onchange('unit_id')
	def onchange_unit_id(self):
		res = {}
		if self.unit_id:
			res['domain'] = {'pricelist': [('product_tmpl_id', '=', self.unit_id.product_id.id)]}
		else:
			res['domain'] = {'pricelist': [('product_tmpl_id', '=', '')]}
		return res


	@api.multi
	def create_order(self):
		order_line = {
			'no_book': self.id,
			'product_id': self.unit_id.product_id.id,
			'name': self.unit_id.product_id.name,
			'product_uom_qty': self.estimation_time,
			'product_uom': self.pricelist.uom_id.id,
			'price_unit': self.price
		}

		order_vals = {
			'partner_id': self.customer_id.id,
			'order_policy': 'manual',
			'partner_invoice_id': self.partner_invoice_id.id,
			'partner_shipping_id': self.partner_shipping_id.id,
			'order_line': [(0, 0, order_line)]
		}

		order_obj = self.env['sale.order']
		res = order_obj.create(order_vals)
		order_obj.button_dummy()

		self.write({'sale_order_id': res.id})
		return res


	@api.multi
	def confirmed_booking(self):

		self.write({'state': 'confirm'})
		booking_line_obj = self.env['dtbs.carrent.unit.booking.line']
		vals = {
			'unit_id': self.unit_id.id,
			'date_start': self.date_rent,
			'date_end': self.date_end,
			'state': 'unassigned',
			'booking_id': self.id,
			}
		booking_line_obj.create(vals)


		if (self.auto_mail==True):
			self.action_confirm_send_mail()

		return True


	@api.multi
	def sale_booking(self):
		self.write({'state': 'sale'})
		return True

	@api.multi
	def rented_booking(self):
		carrent_booking_unit_line_obj = self.env['dtbs.carrent.unit.booking.line']
		carrent_booking_unit_line_ids = carrent_booking_unit_line_obj.search([('booking_id', '=', self.id)])
		for line in carrent_booking_unit_line_ids:
			line.write({'state': 'assigned'})
		self.write({'state': 'rent'})
		return True

	@api.multi
	def cancelled_booking(self):
		carrent_booking_unit_line_obj = self.env['dtbs.carrent.unit.booking.line']
		carrent_booking_unit_line_ids = carrent_booking_unit_line_obj.search([('booking_id', '=', self.id)])
		for line in carrent_booking_unit_line_ids:
			line.write({'state': 'unassigned'})
		self.write({'state': 'cancel'})

		return True

	@api.multi
	def return_booking(self):
		self.write({'state': 'return'})
		return True


	@api.one
	def action_confirm_send_mail(self):
		template_id = self.env.ref('carrent_booking.email_template_booking_confirm')
		template_id.send_mail(self.ids[0], force_send=True)


	@api.multi
	def action_confirm_send_mail_manual(self):
		assert len(self._ids) == 1, 'This is for a single id at a time.'
		ir_model_data = self.env['ir.model.data']
		try:
			template_id = (ir_model_data.get_object_reference('carrent_booking','email_template_booking_confirm')[1])
		except ValueError:
			template_id = False
		try:
			compose_form_id = (ir_model_data.get_object_reference('mail','email_compose_message_wizard_form')[1])
		except ValueError:
			compose_form_id = False
		ctx = dict()
		ctx.update({
			'default_model': 'dtbs.carrent.booking',
			'default_res_id': self._ids[0],
			'default_use_template': bool(template_id),
			'default_template_id': template_id,
			'default_composition_mode': 'comment',
			'force_send': True,
			'mark_so_as_sent': True
		})
		return {
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'mail.compose.message',
			'views': [(compose_form_id, 'form')],
			'view_id': compose_form_id,
			'target': 'new',
			'context': ctx,
			'force_send': True
		}


	@api.model
	def default_get(self, fields):
		"""
		To get default values for the object.
		@param self: The object pointer.
		@param fields: List of fields for which we want default values
		@return: A dictionary which of fields with values.
		"""
		if self._context is None:
			self._context = {}
		res = super(Booking, self).default_get(fields)
		if self._context:
			keys = self._context.keys()
			if 'date_rent' in keys:
				res.update({'date_rent': self._context['date_rent']})
			if 'unit_id' in keys:
				unitid = self._context['unit_id']
				res.update({'unit_id': int(unitid)})
		return res


	@api.model
	def update_booking_to_rent(self):
		date_today = datetime.datetime.today()
		item_ids = self.search([('date_rent', '<=', date_today), ('date_end', '>=', date_today), ('state', '=', 'sale')])
		for record in item_ids:
			record.write({'state': 'rent'})
			
			carrent_booking_unit_line_obj = self.env['dtbs.carrent.unit.booking.line']
			carrent_booking_unit_line_ids = carrent_booking_unit_line_obj.search([('booking_id', '=', record.id)])
			for line in carrent_booking_unit_line_ids:
				line.write({'state': 'assigned'})



	@api.model
	@api.returns('self', lambda value: value.id)
	def create(self, vals):
		# auto number
		if vals.get('no_book','/')=='/':
			vals['no_book'] = self.env['ir.sequence'].get('dtbs.carrent.booking') or '/'
		context = dict({}, mail_create_nolog=True)
		book =  super(Booking, self.with_context({"mail_create_nolog": True})).create(vals)
		return book


# =========  Sale Order Inherit =========== #
class sale_order(models.Model):
	_inherit = 'sale.order'


	@api.multi
	def action_wait(self):
		res = super(sale_order, self).action_wait()
		order_line_obj = self.env['sale.order.line']
		order_line_ids = order_line_obj.search([('order_id','=',self.id)])

		date_today = datetime.datetime.today()

		for line in order_line_ids:
			line.no_book.signal_workflow('sale')

			d_rent_obj = (datetime.datetime.strptime(line.no_book.date_rent, DEFAULT_SERVER_DATE_FORMAT))

			if d_rent_obj <= date_today:
				line.no_book.signal_workflow('rent')

		return res


	@api.multi
	def action_cancel(self):
		res = super(sale_order, self).action_cancel()
		order_line_obj = self.env['sale.order.line']
		order_line_ids = order_line_obj.search([('order_id','=',self.id)])

		for line in order_line_ids:
			if line.no_book.state == 'rent':
				line.no_book.signal_workflow('cancelrent')
			else:
				line.no_book.signal_workflow('cancelsale')

		return res


	@api.multi
	def unlink(self):
		order_line_obj = self.env['sale.order.line']
		order_line_ids = order_line_obj.search([('order_id','=',self.id)])

		for line in order_line_ids:
			line.no_book.write({
				"sales_order_id": None,
				"quotation": False
				})			

		res = super(sale_order, self).unlink()
		return res




# =========  Sale Order Line Inherit =========== #
class sale_order_line(models.Model):
	_inherit = 'sale.order.line'

	no_book = fields.Many2one(comodel_name='dtbs.carrent.booking', string="Booking", change_default=True, readonly=True, states={'draft': [('readonly', False)]})


	@api.multi
	def booking_no_change(self, book_no, partner_id=False):
		if not partner_id:
			raise Warning(WARN_HEAD3, WARN_BOOKING_CHANGE)
		result = {}
		domain = {}
		warning = False


		if book_no:
			booking_obj = self.env['dtbs.carrent.booking']
			booking_obj = booking_obj.browse(book_no)
			
			result['product_id'] = booking_obj.unit_id.product_id.id

		return {'value': result, 'domain': domain, 'warning': warning}


	@api.multi
	def product_id_change_scn(self, book_no, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False,
			fiscal_position=False, flag=False, context=None):
		res = super(sale_order_line, self).product_id_change(
			pricelist, product, qty=qty, uom=uom,
			qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
			lang=lang, update_tax=update_tax, date_order=date_order,
			packaging=packaging, fiscal_position=fiscal_position,
			flag=flag, context=context)

		if book_no and product:
			booking_obj = self.env['dtbs.carrent.booking']
			booking_obj = booking_obj.browse(book_no)

			if 'value' not in res:
				res['value'] = {}
			res['value'].update({
				'product_uom_qty':booking_obj.estimation_time,
				'product_uom':booking_obj.pricelist.uom_id.id,
				'price_unit':booking_obj.price
				})
		return res


	@api.model
	def update_booking_saleorder(self):
		changes = self.search([])
		for record in changes:
			record.no_book.write({
				"sales_order_id": record.order_id.id,
				"quotation": True
				})

		return changes.ids

	@api.model
	def unlink_booking_saleorder(self):
		for record in self:
			record.no_book.write({
				"sales_order_id": None,
				"quotation": False
				})

		return True

	@api.model
	def create(self, vals):
		res = super(sale_order_line, self).create(vals)
		self.update_booking_saleorder()
		return res

	@api.multi
	def unlink(self):
		self.unlink_booking_saleorder()
		res = super(sale_order_line, self).unlink()
		return res


# =========  Booking Unit Lines =========== #
class carrent_unit_booking_line(models.Model):
	_name = 'dtbs.carrent.unit.booking.line'
	_description = 'Unit Booking'
	_rec_name = 'unit_id'

	unit_id = fields.Many2one(comodel_name='dtbs.carrent.unit', string='Unit')
	date_start = fields.Date('Start Date', required=True)
	date_end = fields.Date('End Date', required=True)
	state = fields.Selection(STATE2, 'Unit Status')
	booking_id = fields.Many2one('dtbs.carrent.booking', string='Booking')
	status = fields.Selection(string='State', related='booking_id.state')

carrent_unit_booking_line()


# =========  Unit Inherit =========== #
class Unit(models.Model):
	_inherit = 'dtbs.carrent.unit'
	_description = 'Unit'

	carrent_booking_unit_ids = fields.One2many(comodel_name='dtbs.carrent.unit.booking.line', inverse_name='unit_id', string='Unit Booking Line')


# =========  Booking Summary =========== #
class Bookingsummary(models.Model):

	_name = 'dtbs.carrent.booking.summary'
	_description = 'Unit booking summary'

	date_from = fields.Date('Date From')
	date_to = fields.Date('Date To')
	summary_header = fields.Text('Summary Header')
	unit_summary = fields.Text('Unit Summary')

	@api.model
	def default_get(self, fields):
		"""
		To get default values for the object.
		@param self: The object pointer.
		@param fields: List of fields for which we want default values
		@return: A dictionary which of fields with values.
		"""
		if self._context is None:
			self._context = {}
		res = super(Bookingsummary, self).default_get(fields)
		if not self.date_from and self.date_to:
			date_today = datetime.datetime.today()
			first_day = datetime.datetime(date_today.year, date_today.month, 1, 0, 0, 0)
			first_temp_day = first_day + relativedelta(months=1)
			last_temp_day = first_temp_day - relativedelta(days=1)
			last_day = datetime.datetime(last_temp_day.year,last_temp_day.month,last_temp_day.day, 23, 59, 59)
			date_froms = first_day.strftime(DEFAULT_SERVER_DATE_FORMAT)
			date_ends = last_day.strftime(DEFAULT_SERVER_DATE_FORMAT)
			res.update({'date_from': date_froms, 'date_to': date_ends})
		return res


	@api.onchange('date_from', 'date_to')
	def get_unit_summary(self):
		'''
		@param self: object pointer
		'''
		res = {}
		all_detail = []
		unit_obj = self.env['dtbs.carrent.unit']
		booking_line_obj = self.env['dtbs.carrent.unit.booking.line']
		date_range_list = []
		main_header = []
		summary_header_list = ['Units']
		if self.date_from and self.date_to:
			if self.date_from > self.date_to:
				raise except_orm(WARN_HEAD4, WARN_TIME_PERIOD)
			d_frm_obj = (datetime.datetime.strptime(self.date_from, DEFAULT_SERVER_DATE_FORMAT))
			d_to_obj = (datetime.datetime.strptime(self.date_to, DEFAULT_SERVER_DATE_FORMAT))
			temp_date = d_frm_obj
			while(temp_date <= d_to_obj):
				val = ''
				val = (str(temp_date.strftime("%a")) + ' ' +
						str(temp_date.strftime("%b")) + ' ' +
						str(temp_date.strftime("%d")))
				summary_header_list.append(val)
				date_range_list.append(temp_date.strftime(DEFAULT_SERVER_DATE_FORMAT))
				temp_date = temp_date + datetime.timedelta(days=1)
			all_detail.append(summary_header_list)
			unit_ids = unit_obj.search([])
			all_unit_detail = []
			for unit in unit_ids:
				unit_detail = {}
				unit_list_stats = []
				unit_detail.update({'name': unit.name or ''})
				if not unit.carrent_booking_unit_ids:
					for chk_date in date_range_list:
						unit_list_stats.append({'state': 'Free', 'date': chk_date})
				else:
					for chk_date in date_range_list:
						for unit_res_line in unit.carrent_booking_unit_ids:
							reservline_ids = [i.ids for i in unit.carrent_booking_unit_ids]
							reservline_ids = (booking_line_obj.search
												([('id', 'in', reservline_ids),
												('date_start', '<=', chk_date),
												('date_end', '>=', chk_date),
												('status', 'not in', ['cancel','return'])
												]))
							if reservline_ids:
								unit_list_stats.append({'state': 'Booked',
														'date': chk_date,
														'unit_id': unit.id})
								break
							else:
								unit_list_stats.append({'state': 'Free',
														'date': chk_date,
														'unit_id': unit.id})
								break
				unit_detail.update({'value': unit_list_stats})
				all_unit_detail.append(unit_detail)
			main_header.append({'header': summary_header_list})
			self.summary_header = str(main_header)
			self.unit_summary = str(all_unit_detail)
		return res