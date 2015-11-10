from openerp import models, fields, api, _, netsvc
from openerp.tools import misc, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, ValidationError
from decimal import Decimal
import datetime
import time
import urllib2


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

	no_book = fields.Char(string="Booking Number", readonly=True, track_visibility='onchange')
	state = fields.Selection([('draft', 'Draft'),('confirm', 'Confirm'),('rent', 'On Rent'),('cancel', 'Cancelled'),('return', 'Returned')], string='Status', default='draft',
								track_visibility='onchange')
	customer_id = fields.Many2one(comodel_name="res.partner", string="Customer", required=True, domain=[("customer", "=", True)], states={'draft': [('readonly', False)]},
									track_visibility='onchange')
	date_order = fields.Date('Date Ordered', required=True, readonly=True, states={'draft': [('readonly', False)]},
									default=(lambda *a:time.strftime(DEFAULT_SERVER_DATE_FORMAT)))
	date_rent = fields.Date('Date Rent', required=True, readonly=True, states={'draft': [('readonly', False)]},
									default=(lambda *a:time.strftime(DEFAULT_SERVER_DATE_FORMAT)), track_visibility='onchange')
	warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Rental', readonly=True, required=True, default=1, states={'draft': [('readonly', False)]})
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
	estimation_time = fields.Integer(string="Estimated Time(s)", default=1, required=True)
	time_selection = fields.Selection([('day', 'Day(s)'),('month', 'Month(s)'),('year', 'Year(s)')], string='In', default='day', required=True)
	date_end = fields.Date(string="Estimated Date End", compute="_calc_date_end", store=True)



	_sql_constraints = [
		("Unique Number", "UNIQUE(no_book)", "The Booking Number must be unique"),
	]

	@api.constrains('no_book', 'date_order', 'date_rent')
	def constraint_date_rent(self):
		if self.date_order and self.date_rent:
			if self.date_rent < self.date_order:
				raise except_orm('Warning', 'Rent date should be greater than the order date.')


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

	@api.depends('estimation_time','time_selection')
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
	def confirmed_booking(self):
		self.write({'state': 'confirm'})

		if (self.auto_mail==True):
			self.action_confirm_send_mail()

		return True

	@api.multi
	def rented_booking(self):
		self.write({'state': 'rent'})
		return True

	@api.multi
	def cancelled_booking(self):
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


	def create(self, cr, uid, vals, context=None):
		# auto number
		if vals.get('no_book','/')=='/':
			vals['no_book'] = self.pool.get('ir.sequence').get(cr, uid, 'dtbs.carrent.booking') or '/'
		context = dict(context or {}, mail_create_nolog=True)
		book =  super(Booking, self).create(cr, uid, vals, context=context)
		return book


# ============= Folio =============== #
class folio(models.Model):


	_name = 'dtbs.carrent.folio'
	_description = 'Car Rental Folio New'
	_rec_name = 'name'
	_order = 'id'
	_inherit = ['ir.needaction_mixin']

	name = fields.Char('Folio Number', readonly=True)
	order_id = fields.Many2one(comodel_name='sale.order', string='Order', delegate=True, required=True, ondelete='cascade')
	unit_lines = fields.One2many(comodel_name='dtbs.carrent.folio.line', inverse_name='folio_id', readonly=True, states={'draft': [('readonly', False)],
								'sent': [('readonly', False)]}, help="Unit booking detail.")
	rental_invoice_id = fields.Many2one('account.invoice', 'Invoice')


	def onchange_partner_id(self, cr, uid, ids, part, context=None):
		if not part:
			return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False}}

		part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
		addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])
		val = {
			'partner_invoice_id': addr['invoice'],
			'partner_shipping_id': addr['delivery'],
		}
		return {'value': val}


	@api.multi
	def action_folio_send(self):
		assert len(self._ids) == 1, 'This is for a single id at a time.'
		ir_model_data = self.env['ir.model.data']
		try:
			template_id = (ir_model_data.get_object_reference('carrent_booking','email_template_edi_folio')[1])
		except ValueError:
			template_id = False
		try:
			compose_form_id = (ir_model_data.get_object_reference('mail','email_compose_message_wizard_form')[1])
		except ValueError:
			compose_form_id = False
		ctx = dict()
		ctx.update({
			'default_model': 'dtbs.carrent.folio',
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

	@api.multi
	def print_folio(self):
		'''
		This function prints the sales order and mark it as sent, so that we can see more easily the next step of the workflow
		'''
		assert len(self._ids) == 1, 'This option should only be used for a single id at a time'
		self.signal_workflow('quotation_sent')
		return self.env['report'].get_action(self,'carrent_booking.report_folio')


	@api.multi
	def folio_action_button_confirm(self):
		assert len(self._ids) == 1, 'This option should only be used for a single id at a time.'
		self.signal_workflow('folio_order_confirm')
		return True

	@api.multi
	def folio_action_wait(self):
		for o in self:
			if not o.unit_lines:
				raise Warning(_('Error!'),_('You cannot confirm a sales order which has no line.'))
			noprod = self.folio_test_no_product()
			if (o.order_policy == 'manual') or noprod:
				self.write({'state': 'manual', 'date_confirm': fields.Date.context_today(self)})
			else:
				self.write({'state': 'progress', 'date_confirm': fields.Date.context_today(self)})
			self.unit_lines.write({'state': 'confirmed'})
		return True

	@api.multi
	def folio_test_no_product(self):
		for line in self.unit_lines:
			if line.product_id and (line.product_id.type<>'service'):
				return False
		return True


	def _folio_prepare_procurement_group(self, cr, uid, order, context=None):
		return {'name': order.name, 'partner_id': order.partner_shipping_id.id}


	def folio_procurement_needed(self, cr, uid, ids, context=None):
		#when sale is installed only, there is no need to create procurements, that's only
		#further installed modules (sale_service, sale_stock) that will change this.
		sale_line_obj = self.pool.get('dtbs.carrent.folio.line')
		res = []
		for order in self.browse(cr, uid, ids, context=context):
			res.append(sale_line_obj.folio_need_procurement(cr, uid, [line.id for line in order.order_line], context=context))
		return any(res)


	def _folio_prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
		date_planned = self._folio_get_date_planned(cr, uid, order, line, order.date_order, context=context)
		return {
			'name': line.name,
			'origin': order.name,
			'date_planned': date_planned,
			'product_id': line.product_id.id,
			'product_qty': line.product_uom_qty,
			'product_uom': line.product_uom.id,
			'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
			'product_uos': (line.product_uos and line.product_uos.id) or line.product_uom.id,
			'company_id': order.company_id.id,
			'group_id': group_id,
			'invoice_state': (order.order_policy == 'picking') and '2binvoiced' or 'none',
			'sale_line_id': line.id
		}


	def _folio_get_date_planned(self, cr, uid, order, line, start_date, context=None):
		date_planned = datetime.datetime.strptime(start_date, DEFAULT_SERVER_DATETIME_FORMAT) + datetime.timedelta(days=line.delay or 0.0)
		return date_planned


	@api.multi
	def folio_action_ship_create(self):
		"""Create the required procurements to supply sales order lines, also connecting
		the procurements to appropriate stock moves in order to bring the goods to the
		sales order's requested location.

		:return: True
		"""
		procurement_obj = self.pool.get('procurement.order')
		sale_line_obj = self.pool.get('dtbs.carrent.folio.line')
		for order in self.browse(cr, uid, ids, context=context):
			proc_ids = []
			vals = self._folio_prepare_procurement_group(cr, uid, order, context=context)
			if not order.procurement_group_id:
				group_id = self.pool.get("procurement.group").create(cr, uid, vals, context=context)
				order.write({'procurement_group_id': group_id})

			for line in order.unit_lines:
				#Try to fix exception procurement (possible when after a shipping exception the user choose to recreate)
				if line.procurement_ids:
					#first check them to see if they are in exception or not (one of the related moves is cancelled)
					procurement_obj.check(cr, uid, [x.id for x in line.procurement_ids if x.state not in ['cancel', 'done']])
					line.refresh()
					#run again procurement that are in exception in order to trigger another move
					proc_ids += [x.id for x in line.procurement_ids if x.state in ('exception', 'cancel')]
					procurement_obj.reset_to_confirmed(cr, uid, proc_ids, context=context)
				elif sale_line_obj.folio_need_procurement(cr, uid, [line.id], context=context):
					if (line.state == 'done') or not line.product_id:
						continue
					vals = self._folio_prepare_order_line_procurement(cr, uid, order, line, group_id=order.procurement_group_id.id, context=context)
					proc_id = procurement_obj.create(cr, uid, vals, context=context)
					proc_ids.append(proc_id)
			#Confirm procurement order such that rules will be applied on it
			#note that the workflow normally ensure proc_ids isn't an empty list
			procurement_obj.run(cr, uid, proc_ids, context=context)

			#if shipping was in exception and the user choose to recreate the delivery order, write the new status of SO
			if order.state == 'shipping_except':
				val = {'state': 'progress', 'shipped': False}

				if (order.order_policy == 'manual'):
					for line in order.unit_lines:
						if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
							val['state'] = 'manual'
							break
				order.write(val)
		return True


	def folio_action_view_delivery(self, cr, uid, ids, context=None):
		'''
		This function returns an action that display existing delivery orders
		of given sales order ids. It can either be a in a list or in a form
		view, if there is only one delivery order to show.
		'''

		mod_obj = self.pool.get('ir.model.data')
		act_obj = self.pool.get('ir.actions.act_window')

		result = mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree_all')
		id = result and result[1] or False
		result = act_obj.read(cr, uid, [id], context=context)[0]

		#compute the number of delivery orders to display
		pick_ids = []
		for so in self.browse(cr, uid, ids, context=context):
			pick_ids += [picking.id for picking in so.picking_ids]
            
		#choose the view_mode accordingly
		if len(pick_ids) > 1:
			result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
		else:
			res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
			result['views'] = [(res and res[1] or False, 'form')]
			result['res_id'] = pick_ids and pick_ids[0] or False
		return result


	@api.multi
	def folio_action_cancel(self):
		sale_order_line_obj = self.env['dtbs.carrent.folio.line']
		account_invoice_obj = self.env['account.invoice']
		for sale in self:
			for inv in sale.invoice_ids:
				if inv.state not in ('draft', 'cancel'):
					raise Warning(
						_('Cannot cancel this sales order!'),
						_('First cancel all invoices attached to this sales order.'))
				inv.signal_workflow('folio_invoice_cancel')
			sale_order_line_obj.write({'state': 'cancel'})
		self.write({'state': 'cancel'})
		return True



	@api.multi
	def folio_action_invoice_create(self, grouped=False, states=None):
		if states is None:
			states = ['confirmed', 'done']
		order_ids = [folio.order_id.id for folio in self]
		unit_lst = []
		sale_obj = self.env['sale.order'].browse(order_ids)
		invoice_id = (sale_obj.action_invoice_create(grouped=False, states=['confirmed', 'done']))
		for line in self:
			values = {'invoiced': True,
					'state': 'progress' if grouped else 'progress',
					'rental_invoice_id': invoice_id
					}
			line.write(values)
			# for line2 in line.folio_pos_order_ids:
			# 	line2.write({'invoice_id': invoice_id})
			# 	line2.action_invoice_state()
			for rec in line.unit_lines:
				unit_lst.append(rec.product_id)
			for unit in unit_lst:
				unit_obj = self.env['dtbs.carrent.unit'].search([('name', '=', unit.name)])
				#unit_obj.write({'isvehicle': True})
		return invoice_id



	@api.model
	def create(self, vals):
		# auto number
		if vals.get('name','/')=='/':
			vals['name'] = self.env['ir.sequence'].get('dtbs.carrent.folio') or '/'
		context = dict({}, mail_create_nolog=True)
		fol =  super(folio, self).create(vals)
		return fol

	@api.multi
	def unlink(self):
		sale_line_obj = self.env['sale.order']
		for order in self:
			if order.order_id:
				sale_unlink_obj = (sale_line_obj.browse([order.order_id.id]))
				sale_unlink_obj.unlink()
		return super(folio, self).unlink()


class Folio_line(models.Model):

	def folio_need_procurement(self, cr, uid, ids, context=None):
		#when sale is installed only, there is no need to create procurements, that's only
		#further installed modules (sale_service, sale_stock) that will change this.
		prod_obj = self.pool.get('product.product')
		for line in self.browse(cr, uid, ids, context=context):
			if prod_obj.need_procurement(cr, uid, [line.product_id.id], context=context):
				return True
		return False

	_name = 'dtbs.carrent.folio.line'
	_description = 'Rental folio unit line'

	order_line_id = fields.Many2one(comodel_name='sale.order.line', string='Order Line', required=True, delegate=True, ondelete='cascade')
	folio_id = fields.Many2one(comodel_name='dtbs.carrent.folio', string='Folio', ondelete='cascade')
	booking_id = fields.Many2one(comodel_name='dtbs.carrent.booking', string='Booking Number', required=True)
	police = fields.Char(compute="_get_booking", string="Police Number", store=True)



	@api.onchange('booking_id')
	def onchange_booking_id(self):
		if self.booking_id:
			self.name = self.booking_id.no_book
			self.product_id = self.booking_id.unit_id.product_id.id
			self.price_unit = self.booking_id.price
			self.product_uom_qty = self.booking_id.estimation_time
			self.product_uom = self.booking_id.pricelist.uom_id.id

	@api.depends('booking_id')
	def _get_booking(self):
		if self.booking_id:
			self.police = self.booking_id.police


	@api.model
	def create(self, vals, check=True):
		"""
		Overrides orm create method.
		@param self: The object pointer
		@param vals: dictionary of fields value.
		@return: new record set for hotel folio line.
		"""
		if 'folio_id' in vals:
			folio = self.env["dtbs.carrent.folio"].browse(vals['folio_id'])
			vals.update({'order_id': folio.order_id.id})
		return super(Folio_line, self).create(vals)


	@api.multi
	def unlink(self):
		sale_line_obj = self.env['sale.order.line']
		for line in self:
			if line.order_line_id:
				sale_unlink_obj = (sale_line_obj.browse([line.order_line_id.id]))
				sale_unlink_obj.unlink()
		return super(Folio_line, self).unlink()