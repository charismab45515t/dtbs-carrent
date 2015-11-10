from openerp import models, fields, api, _, netsvc
from openerp.tools import misc, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, ValidationError
from decimal import Decimal
import datetime
import time
import urllib2


# =========  Brand =========== #
class Brand(models.Model):
	_name = "dtbs.carrent.brand"
	_description = "Brand"

	name = fields.Char("Name", size=50, required=True)


# =========  Color =========== #
class Color(models.Model):
	_name = "dtbs.carrent.color"
	_description = "Color"

	name = fields.Char("Color", size=50, required=True)


# ========= Categories ============ #
class product_category(models.Model):
	_inherit = "product.category"

	isvehiclecat = fields.Boolean('Is Vehicle Category')

class Category(models.Model):
	_name = "dtbs.carrent.category"
	_description = "Category"

	cat_id = fields.Many2one(comodel_name="product.category", string="Category", required=True, delegate=True, select=True, ondelete='cascade')


# ========= Amenity ============= #
class Facility(models.Model):
	_name = "dtbs.carrent.facility"
	_description = "Facility"

	name = fields.Char(string="Facility", size=50, required=True)
	desc = fields.Text(string="Description")


# ============ Unit ==============#
 
class product_template(models.Model):
	_inherit = "product.template"

	isvehicle = fields.Boolean('Is Available', default=True)


class Unit(models.Model):
	_name = "dtbs.carrent.unit"
	_description = "Vehicle"

	product_id = fields.Many2one(comodel_name='product.template', string='Product_id', required=True, delegate=True, ondelete='cascade')

	code = fields.Char(string="Vehicle Code", size=50, required=True)
	police = fields.Char(string="Police Number", size=20, required=True)
	brand_id = fields.Many2one(comodel_name="dtbs.carrent.brand", string="Brand", required=True)
	color = fields.Many2one(comodel_name="dtbs.carrent.color", string="Color")
	capacity = fields.Integer(string="Capacity")
	chassis = fields.Char(string="Chassis Number", size=50)
	engine = fields.Char(string="Engine Number", size=50)
	year = fields.Integer(string="Production Year")
	desc = fields.Text(string="Description")
	facility_ids = fields.Many2many(comodel_name="dtbs.carrent.facility", string="Facility")
	stnk = fields.Date(string="VRC Due Date", required=True)
	engine_oil = fields.Integer("Engine Oil Every (Km)")
	service = fields.Integer("Service Every (Km)")
	status = fields.Selection([('available', 'Available'),('occupied', 'Occupied')], string='Current Status', default='available')
	unit_line_ids = fields.One2many(comodel_name='dtbs.carrent.folio.unit.line', inverse_name='name', string='Unit Reservation Line')
	kanban_color = fields.Integer()


	_sql_constraints = [
		("Unique Code", "UNIQUE(code)", "The car code must be unique"),
		("Unique Police", "UNIQUE(police)", "The police number must be unique"),
	]

	@api.onchange('isvehicle')
	def isvehicle_change(self):
		'''
		Based on isvehicle, status will be updated.
		----------------------------------------
		@param self: object pointer
		'''
		if self.isvehicle is False:
			self.status = 'occupied'
		if self.isvehicle is True:
			self.status = 'available'


	@api.multi
	def write(self, vals):
		"""
		Overrides orm write method.
		@param self: The object pointer
		@param vals: dictionary of fields value.
		"""
		if 'isvehicle' in vals and vals['isvehicle'] is False:
			vals.update({'kanban_color': 2, 'status': 'occupied'})
		if 'isvehicle'in vals and vals['isvehicle'] is True:
			vals.update({'kanban_color': 5, 'status': 'available'})
		ret_val = super(Unit, self).write(vals)
		return ret_val

	@api.multi
	def set_vehicle_status_occupied(self):
		"""
		This method is used to change the state
		to occupied of the unit.
		---------------------------------------
		@param self: object pointer
        """
		return self.write({'isvehicle': False, 'kanban_color': 2})

	@api.multi
	def set_vehicle_status_available(self):
		"""
		This method is used to change the state
		to available of the unit.
		---------------------------------------
		@param self: object pointer
		"""
		return self.write({'isvehicle': True, 'kanban_color': 5})


# ============ Folio Unit =========== #
class folio_unit_line(models.Model):
	_name = 'dtbs.carrent.folio.unit.line'
	_description = 'Unit Reservation'
	_rec_name = 'name'

	name = fields.Many2one(comodel_name='dtbs.carrent.unit', string='Unit id')
	check_in = fields.Date(string='Begin Date', required=True)
	check_out = fields.Date(string='End Date', required=True)
	folio_id = fields.Many2one(comodel_name='dtbs.carrent.folio', string='Folio Number')
	status = fields.Selection(string='state', related='folio_id.state')


# ============= Folio =============== #
class folio(models.Model):

	@api.multi
	def name_get(self):
		res = []
		disp = ''
		for rec in self:
			if rec.order_id:
				disp = str(rec.name)
				res.append((rec.id, disp))
		return res

	@api.model
	def name_search(self, name='', args=None, operator='ilike', limit=100):
		if args is None:
			args = []
		args += ([('name', operator, name)])
		mids = self.search(args, limit=100)
		return mids.name_get()

	@api.model
	def _needaction_count(self, domain=None):
		"""
		Show a count of draft state folio on the menu badge.
		@param self: object pointer
		"""
		return self.search_count([('state', '=', 'draft')])

	@api.multi
	def copy(self, default=None):
		'''
		@param self: object pointer
		@param default: dict of default values to be set
		'''
		return self.env['sale.order'].copy(default=default)

	@api.multi
	def _invoiced(self, name, arg):
		'''
		@param self: object pointer
		@param name: Names of fields.
		@param arg: User defined arguments
		'''
		return self.env['sale.order']._invoiced(name, arg)

	@api.multi
	def _invoiced_search(self, obj, name, args):
		'''
		@param self: object pointer
		@param name: Names of fields.
		@param arg: User defined arguments
		'''
		return self.env['sale.order']._invoiced_search(obj, name, args)


	_name = 'dtbs.carrent.folio'
	_description = 'Hotel Folio New'
	_rec_name = 'order_id'
	_order = 'id'
	_inherit = ['ir.needaction_mixin']

	name = fields.Char('Folio Number', readonly=True)
	order_id = fields.Many2one(comodel_name='sale.order', string='Order', delegate=True, required=True, ondelete='cascade')
	checkin_date = fields.Date(string='Begin', required=True, readonly=True, states={'draft': [('readonly', False)]})
	checkout_date = fields.Date(string='End', required=True, readonly=True, states={'draft': [('readonly', False)]})
	unit_lines = fields.One2many(comodel_name='dtbs.carrent.folio.line', inverse_name='folio_id', readonly=True, states={'draft': [('readonly', False)],
								'sent': [('readonly', False)]}, help="Unit reservation detail.")
	rental_policy = fields.Selection([('prepaid', 'On Booking'), ('manual', 'On Check In'), ('picking', 'On Checkout')],
									'Rental Policy', default='manual', help="Rental policy for payment that "
									"either the customer has to payment at booking time or begin end time.")
	duration = fields.Float('Duration in Days', help="Number of days which will automatically count from the begin and end date. ")
	currrency_ids = fields.One2many(comodel_name='currency.exchange', inverse_name='folio_no', readonly=True)
	rental_invoice_id = fields.Many2one('account.invoice', 'Invoice')


	@api.multi
	def go_to_currency_exchange(self):
		'''
		 when Money Exchange button is clicked then this method is called.
		-------------------------------------------------------------------
		@param self: object pointer
		'''
		cr, uid, context = self.env.args
		context = dict(context)
		for rec in self:
			if rec.partner_id.id and len(rec.unit_lines) != 0:
				context.update({'folioid': rec.id, 'customer': rec.partner_id.id,
								'unit_no': rec.unit_lines[0].product_id.name,
								'rental': rec.warehouse_id.id})
				self.env.args = cr, uid, misc.frozendict(context)
			else:
				raise except_orm('Warning', 'Please Reserve Any Unit.')
		return {'name': _('Currency Exchange'),
				'res_model': 'currency.exchange',
				'type': 'ir.actions.act_window',
				'view_id': False,
				'view_mode': 'form,tree',
				'view_type': 'form',
				'context': {'default_folio_no': context.get('folioid'),
							'default_rental_id': context.get('rental'),
							'default_customer_name': context.get('customer'),
							'default_unit_number': context.get('unit_no')
							},
				}

	@api.constrains('unit_lines')
	def folio_unit_lines(self):
		'''
		This method is used to validate the unit_lines.
		------------------------------------------------
		@param self: object pointer
		@return: raise warning depending on the validation
		'''
		folio_units = []
		for unit in self[0].unit_lines:
			if unit.product_id.id in folio_units:
				raise ValidationError('You Cannot Take Same Unit Twice')
			folio_units.append(unit.product_id.id)

	@api.constrains('checkin_date', 'checkout_date')
	def check_dates(self):
		'''
		This method is used to validate the checkin_date and checkout_date.
		-------------------------------------------------------------------
		@param self: object pointer
		@return: raise warning depending on the validation
		'''
		if self.checkin_date > self.checkout_date:
			raise ValidationError('Begin Date Should be less than or equal the End Date!')
		if self.date_order and self.checkin_date:
			if self.date_order > self.checkin_date:
				raise ValidationError('Begin date should be greater than or equal the current date.')


	@api.onchange('checkout_date', 'checkin_date')
	def onchange_dates(self):
		'''
		This mathod gives the duration between check in and checkout
		if customer will leave only for some hour it would be considers
		as a whole day.If customer will check in checkout for more or equal
		hours, which configured in company as additional hours than it would
		be consider as full days
		--------------------------------------------------------------------
		@param self: object pointer
		@return: Duration and checkout_date
		'''
		company_obj = self.env['res.company']
		configured_addition_hours = 0
		company_ids = company_obj.search([])
		if company_ids.ids:
			configured_addition_hours = company_ids[0].additional_hours
		myduration = 0
		if self.checkin_date and self.checkout_date:
			chkin_dt = (datetime.datetime.strptime(self.checkin_date, DEFAULT_SERVER_DATE_FORMAT))
			chkout_dt = (datetime.datetime.strptime(self.checkout_date, DEFAULT_SERVER_DATE_FORMAT))
			dur = chkout_dt - chkin_dt
			myduration = dur.days + 1
			if configured_addition_hours > 0:
				additional_hours = abs((dur.seconds / 60) / 60)
				if additional_hours >= configured_addition_hours:
					myduration += 1
		self.duration = myduration

	@api.model
	def create(self, vals, check=True):
		"""
		Overrides orm create method.
		@param self: The object pointer
		@param vals: dictionary of fields value.
		@return: new record set for hotel folio.
		"""
		if 'folio_id' in vals:
			tmp_unit_lines = vals.get('unit_lines', [])
			vals['order_policy'] = vals.get('rental_policy', 'manual')
			vals.update({'unit_lines': []})
			folio_id = super(folio, self).create(vals)
			for line in (tmp_unit_lines):
				line[2].update({'folio_id': folio_id})
			vals.update({'unit_lines': tmp_unit_lines})
			folio_id.write(vals)
		else:
			if not vals:
				vals = {}
			vals['name'] = self.env['ir.sequence'].get('dtbs.carrent.folio')
			folio_id = super(folio, self).create(vals)
			folio_unit_line_obj = self.env['dtbs.carrent.folio.unit.line']
			h_unit_obj = self.env['dtbs.carrent.unit']
			unit_lst = []
			for rec in folio_id:
				if not rec.reservation_id:
					for unit_rec in rec.unit_lines:
						unit_lst.append(unit_rec.product_id)
					for rm in unit_lst:
						unit_obj = h_unit_obj.search([('name', '=', rm.name)])
						#unit_obj.write({'isvehicle': False})
						vals = {'unit_id': unit_obj.id,
								'check_in': rec.checkin_date,
								'check_out': rec.checkout_date,
								'folio_id': rec.id,
								}
						folio_unit_line_obj.create(vals)
		return folio_id

	@api.multi
	def write(self, vals):
		"""
		Overrides orm write method.
		@param self: The object pointer
		@param vals: dictionary of fields value.
		"""
		folio_unit_line_obj = self.env['dtbs.carrent.folio.unit.line']
		reservation_line_obj = self.env['dtbs.carrent.unit.reservation.line']
		product_obj = self.env['product.template']
		h_unit_obj = self.env['dtbs.carrent.unit']
		unit_lst1 = []
		for rec in self:
			for res in rec.unit_lines:
				unit_lst1.append(res.product_id.id)
		folio_write = super(folio, self).write(vals)
		unit_lst = []
		for folio_obj in self:
			for folio_rec in folio_obj.unit_lines:
				unit_lst.append(folio_rec.product_id.id)
			new_units = set(unit_lst).difference(set(unit_lst1))
			if len(list(new_units)) != 0:
				unit_list = product_obj.browse(list(new_units))
				for rm in unit_list:
					unit_obj = h_unit_obj.search([('name', '=', rm.name)])
					#unit_obj.write({'isvehicle': False})
					vals = {'unit_id': unit_obj.id,
							'check_in': folio_obj.checkin_date,
							'check_out': folio_obj.checkout_date,
							'folio_id': folio_obj.id,
							}
					folio_unit_line_obj.create(vals)
			if len(list(new_units)) == 0:
				unit_list_obj = product_obj.browse(unit_lst1)
				for rom in unit_list_obj:
					unit_obj = h_unit_obj.search([('name', '=', rom.name)])
					#unit_obj.write({'isvehicle': False})
					unit_vals = {'unit_id': unit_obj.id,
								'check_in': folio_obj.checkin_date,
								'check_out': folio_obj.checkout_date,
								'folio_id': folio_obj.id,
								}
					folio_romline_rec = (folio_unit_line_obj.search([('folio_id', '=', folio_obj.id)]))
					folio_romline_rec.write(unit_vals)
			if folio_obj.reservation_id:
				for reservation in folio_obj.reservation_id:
					reservation_obj = (reservation_line_obj.search([('reservation_id', '=', reservation.id)]))
					if len(reservation_obj) == 1:
						for line_id in reservation.bookingunit_ids:
							line_id = line_id.reserve
							for unit_id in line_id:
								vals = {'unit_id': unit_id.id,
										'check_in': folio_obj.checkin_date,
										'check_out': folio_obj.checkout_date,
										'state': 'assigned',
										'reservation_id': reservation.id,
										}
								reservation_obj.write(vals)
		return folio_write

	@api.onchange('warehouse_id')
	def onchange_warehouse_id(self):
		'''
		When you change warehouse it will update the warehouse of
		the rental folio as well
		----------------------------------------------------------
		@param self: object pointer
		'''
		for folio in self:
			order = folio.order_id
			x = order.onchange_warehouse_id(folio.warehouse_id.id)
		return x

	@api.onchange('partner_id')
	def onchange_partner_id(self):
		'''
		When you change partner_id it will update the partner_invoice_id,
		partner_shipping_id and pricelist_id of the rental folio as well
		---------------------------------------------------------------
		@param self: object pointer
		'''
		if self.partner_id:
			partner_rec = self.env['res.partner'].browse(self.partner_id.id)
			order_ids = [folio.order_id.id for folio in self]
			if not order_ids:
				self.partner_invoice_id = partner_rec.id
				self.partner_shipping_id = partner_rec.id
				self.pricelist_id = partner_rec.property_product_pricelist.id
				raise Warning('Not Any Order For  %s ' % (partner_rec.name))
			else:
				self.partner_invoice_id = partner_rec.id
				self.partner_shipping_id = partner_rec.id
				self.pricelist_id = partner_rec.property_product_pricelist.id

	@api.multi
	def action_view_delivery(self):
		for folio in self:
			order = folio.order_id
			x = order.action_view_delivery()
		return x

	@api.multi
	def button_dummy(self):
		'''
		@param self: object pointer
		'''
		for folio in self:
			order = folio.order_id
			x = order.button_dummy()
		return x

	@api.multi
	def action_invoice_create(self, grouped=False, states=None):
		'''
		@param self: object pointer
		'''
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

	@api.multi
	def action_invoice_cancel(self):
		'''
		@param self: object pointer
		'''
		order_ids = [folio.order_id.id for folio in self]
		sale_obj = self.env['sale.order'].browse(order_ids)
		res = sale_obj.action_invoice_cancel()
		for sale in self:
			for line in sale.order_line:
				line.write({'invoiced': 'invoiced'})
		sale.write({'state': 'invoice_except'})
		return res

	@api.multi
	def action_cancel(self):
		'''
		@param self: object pointer
		'''
		order_ids = [folio.order_id.id for folio in self]
		sale_obj = self.env['sale.order'].browse(order_ids)
		rv = sale_obj.action_cancel()
		wf_service = netsvc.LocalService("workflow")
		for sale in self:
			for pick in sale.picking_ids:
				wf_service.trg_validate(self._uid, 'stock.picking', pick.id,'button_cancel', self._cr)
			for invoice in sale.invoice_ids:
				wf_service.trg_validate(self._uid, 'account.invoice', invoice.id, 'invoice_cancel', self._cr)
				sale.write({'state': 'cancel'})
			# for rec in sale.folio_pos_order_ids:
			# 	rec.write({'state': 'cancel'})
		return rv

	@api.multi
	def action_wait(self):
		'''
		@param self: object pointer
		'''
		sale_order_obj = self.env['sale.order']
		res = False
		for o in self:
			sale_obj = sale_order_obj.browse([o.order_id.id])
			res = sale_obj.action_wait()
			if (o.order_policy == 'manual') and (not o.invoice_ids):
				o.write({'state': 'manual'})
			else:
				o.write({'state': 'progress'})
		return res

	@api.multi
	def test_state(self, mode):
		'''
		@param self: object pointer
		@param mode: state of workflow
		'''
		write_done_ids = []
		write_cancel_ids = []
		if write_done_ids:
			test_obj = self.env['sale.order.line'].browse(write_done_ids)
			test_obj.write({'state': 'done'})
		if write_cancel_ids:
			test_obj = self.env['sale.order.line'].browse(write_cancel_ids)
			test_obj.write({'state': 'cancel'})

	@api.multi
	def action_ship_create(self):
		'''
		@param self: object pointer
		'''
		for folio in self:
			order = folio.order_id
			x = order.action_ship_create()
		return x

	@api.multi
	def action_ship_end(self):
		'''
		@param self: object pointer
		'''
		for order in self:
			order.write({'shipped': True})


	@api.multi
	def has_stockable_products(self):
		'''
		@param self: object pointer
		'''
		for folio in self:
			order = folio.order_id
			x = order.has_stockable_products()
		return x

	@api.multi
	def action_cancel_draft(self):
		'''
		@param self: object pointer
		'''
		if not len(self._ids):
			return False
		query = "select id from sale_order_line where order_id IN %s and state=%s"
		self._cr.execute(query, (tuple(self._ids), 'cancel'))
		cr1 = self._cr
		line_ids = map(lambda x: x[0], cr1.fetchall())
		self.write({'state': 'draft', 'invoice_ids': [], 'shipped': 0})
		sale_line_obj = self.env['sale.order.line'].browse(line_ids)
		sale_line_obj.write({'invoiced': False, 'state': 'draft','invoice_lines': [(6, 0, [])]})
		wf_service = netsvc.LocalService("workflow")
		for inv_id in self._ids:
			# Deleting the existing instance of workflow for SO
			wf_service.trg_delete(self._uid, 'sale.order', inv_id, self._cr)
			wf_service.trg_create(self._uid, 'sale.order', inv_id, self._cr)
		for (id, name) in self.name_get():
			message = _("The sales order '%s' has been set in draft state.") % (name,)
			self.log(message)
		return True


class Folio_line(models.Model):

	@api.one
	def copy(self, default=None):
		'''
		@param self: object pointer
		@param default: dict of default values to be set
		'''
		return self.env['sale.order.line'].copy(default=default)

	@api.multi
	def _amount_line(self, field_name, arg):
		'''
		@param self: object pointer
		@param field_name: Names of fields.
		@param arg: User defined arguments
		'''
		return self.env['sale.order.line']._amount_line(field_name, arg)

	@api.multi
	def _number_packages(self, field_name, arg):
		'''
		@param self: object pointer
		@param field_name: Names of fields.
		@param arg: User defined arguments
		'''
		return self.env['sale.order.line']._number_packages(field_name, arg)

	@api.model
	def _get_checkin_date(self):
		if 'checkin' in self._context:
			return self._context['checkin']
		return time.strftime(DEFAULT_SERVER_DATE_FORMAT)

	@api.model
	def _get_checkout_date(self):
		if 'checkout' in self._context:
			return self._context['checkout']
		return time.strftime(DEFAULT_SERVER_DATE_FORMAT)

	_name = 'dtbs.carrent.folio.line'
	_description = 'Rental folio1 unit line'

	order_line_id = fields.Many2one(comodel_name='sale.order.line', string='Order Line', required=True, delegate=True, ondelete='cascade')
	folio_id = fields.Many2one(comodel_name='dtbs.carrent.folio', string='Folio', ondelete='cascade')
	checkin_date = fields.Date(string='Begin', required=True, default=_get_checkin_date)
	checkout_date = fields.Date(string='End', required=True, default=_get_checkout_date)

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
		"""
		Overrides orm unlink method.
		@param self: The object pointer
		@return: True/False.
		"""
		sale_line_obj = self.env['sale.order.line']
		fr_obj = self.env['dtbs.carrent.folio.unit.line']
		for line in self:
			if line.order_line_id:
				sale_unlink_obj = (sale_line_obj.browse([line.order_line_id.id]))
				for rec in sale_unlink_obj:
					unit_obj = self.env['dtbs.carrent.unit'].search([('name', '=', rec.name)])
					if unit_obj.id:
						folio_arg = [('folio_id', '=', line.folio_id.id), ('unit_id', '=', unit_obj.id)]
						for unit_line in unit_obj.unit_line_ids:
							folio_unit_line_myobj = fr_obj.search(folio_arg)
							if folio_unit_line_myobj.id:
								folio_unit_line_myobj.unlink()
								# unit_obj.write({'isvehicle': True,'status': 'available'})
				sale_unlink_obj.unlink()
		return super(Folio_line, self).unlink()

	@api.multi
	def uos_change(self, product_uos, product_uos_qty=0, product_id=None):
		'''
		@param self: object pointer
		'''
		for folio in self:
			line = folio.order_line_id
			x = line.uos_change(product_uos, product_uos_qty=0, product_id=None)
		return x

	@api.multi
	def product_id_change(self, pricelist, product, qty=0, uom=False,
							qty_uos=0, uos=False, name='', partner_id=False,
							lang=False, update_tax=True, date_order=False):
		'''
		@param self: object pointer
		'''
		line_ids = [folio.order_line_id.id for folio in self]
		if product:
			sale_line_obj = self.env['sale.order.line'].browse(line_ids)
			return sale_line_obj.product_id_change(pricelist, product, qty=0,
													uom=False, qty_uos=0,
													uos=False, name='',
													partner_id=partner_id,
													lang=False,
													update_tax=True,
													date_order=False)

	@api.multi
	def product_uom_change(self, pricelist, product, qty=0,
							uom=False, qty_uos=0, uos=False, name='',
							partner_id=False, lang=False, update_tax=True,
							date_order=False):
		'''
		@param self: object pointer
		'''
		if product:
			return self.product_id_change(pricelist, product, qty=0,
										uom=False, qty_uos=0, uos=False,
										name='', partner_id=partner_id,
										lang=False, update_tax=True,
										date_order=False)

	@api.onchange('checkin_date', 'checkout_date')
	def on_change_checkout(self):
		'''
		When you change checkin_date or checkout_date it will checked it
		and update the qty of rental folio line
		-----------------------------------------------------------------
		@param self: object pointer
		'''
		if not self.checkin_date:
			self.checkin_date = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
		if not self.checkout_date:
			self.checkout_date = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
		if self.checkout_date < self.checkin_date:
			raise except_orm('Warning', 'End must be greater or equal to Begin date')
		if self.checkin_date and self.checkout_date:
			date_a = time.strptime(self.checkout_date, DEFAULT_SERVER_DATE_FORMAT)[:5]
			date_b = time.strptime(self.checkin_date, DEFAULT_SERVER_DATE_FORMAT)[:5]
			diffDate = datetime.datetime(*date_a) - datetime.datetime(*date_b)
			qty = diffDate.days + 1
			self.product_uom_qty = qty

	@api.multi
	def button_confirm(self):
		'''
		@param self: object pointer
		'''
		for folio in self:
			line = folio.order_line_id
			x = line.button_confirm()
		return x

	@api.multi
	def button_done(self):
		'''
		@param self: object pointer
		'''
		line_ids = [folio.order_line_id.id for folio in self]
		sale_line_obj = self.env['sale.order.line'].browse(line_ids)
		res = sale_line_obj.button_done()
		wf_service = netsvc.LocalService("workflow")
		res = self.write({'state': 'done'})
		for line in self:
			wf_service.trg_write(self._uid, 'sale.order', line.order_line_id.order_id.id, self._cr)
		return res

	@api.one
	def copy_data(self, default=None):
		'''
		@param self: object pointer
		@param default: dict of default values to be set
		'''
		line_id = self.order_line_id.id
		sale_line_obj = self.env['sale.order.line'].browse(line_id)
		return sale_line_obj.copy_data(default=default)


# ============ Company ========= #
class res_company(models.Model):

	_inherit = 'res.company'

	additional_hours = fields.Integer(string='Additional Hours',
										help="Provide the min hours value for check in, checkout days, whatever the hours will be provided here based on that extra days will be calculated.")


# ============ Exchange Rate ========== #
class CurrencyExchangeRate(models.Model):

	_name = "currency.exchange"
	_description = "Currency"

	name = fields.Char(string='Reg Number', readonly=True)
	today_date = fields.Date(string='Date Ordered', required=True, default=(lambda *a:time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)))
	input_curr = fields.Many2one(comodel_name='res.currency', string='Input Currency', track_visibility='always')
	in_amount = fields.Float(string='Amount Taken', size=64, default=1.0)
	out_curr = fields.Many2one(comodel_name='res.currency', string='Output Currency', track_visibility='always')
	out_amount = fields.Float(string='Subtotal', size=64)
	folio_no = fields.Many2one(comodel_name='dtbs.carrent.folio', string='Folio Number')
	customer_name = fields.Many2one(comodel_name='res.partner', string='Customer Name')
	unit_number = fields.Char(string='Unit Number')
	state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], 'State', default='draft')
	rate = fields.Float(string='Rate(per unit)', size=64)
	rental_id = fields.Many2one(comodel_name='stock.warehouse', string='Rental Name')
	type = fields.Selection([('cash', 'Cash')], string='Type', default='cash')
	tax = fields.Selection([('2', '2%'), ('5', '5%'), ('10', '10%')], string='Service Tax', default='2')
	total = fields.Float(string='Amount Given')


	@api.model
	def create(self, vals):
		"""
		Overrides orm create method.
		@param self: The object pointer
		@param vals: dictionary of fields value.
		"""
		if not vals:
			vals = {}
		if self._context is None:
			self._context = {}
		vals['name'] = self.env['ir.sequence'].get('currency.exchange')
		return super(CurrencyExchangeRate, self).create(vals)

	@api.onchange('folio_no')
	def get_folio_no(self):
		'''
		When you change folio_no, based on that it will update
		the customer_name,rental_id and unit_number as well
		---------------------------------------------------------
		@param self: object pointer
		'''
		for rec in self:
			self.customer_name = False
			self.rental_id = False
			self.unit_number = False
			if rec.folio_no and len(rec.folio_no.unit_lines) != 0:
				self.customer_name = rec.folio_no.partner_id.id
				self.rental_id = rec.folio_no.warehouse_id.id
				self.unit_number = rec.folio_no.unit_lines[0].product_id.name

	@api.multi
	def act_cur_done(self):
		"""
		This method is used to change the state
		to done of the currency exchange
		---------------------------------------
		@param self: object pointer
		"""
		self.write({'state': 'done'})
		return True


	@api.model
	def get_rate(self, a, b):
		'''
		Calculate rate between two currency
		-----------------------------------
		@param self: object pointer
		'''
		try:
			url = 'http://finance.yahoo.com/d/quotes.csv?s=%s%s=X&f=l1' % (a,b)
			rate = urllib2.urlopen(url).read().rstrip()
			return Decimal(rate)
		except:
			return Decimal('-1.00')

	@api.onchange('input_curr', 'out_curr', 'in_amount')
	def get_currency(self):
		'''
		When you change input_curr, out_curr or in_amount
		it will update the out_amount of the currency exchange
		------------------------------------------------------
		@param self: object pointer
		'''
		self.out_amount = 0.0
		if self.input_curr:
			for rec in self:
				result = rec.get_rate(self.input_curr.name,self.out_curr.name)
				if self.out_curr:
					self.rate = result
					if self.rate == Decimal('-1.00'):
						raise except_orm('Warning','Please Check Your Network Connectivity.')
					self.out_amount = (float(result) * float(self.in_amount))

	@api.onchange('out_amount', 'tax')
	def tax_change(self):
		'''
		When you change out_amount or tax
		it will update the total of the currency exchange
		-------------------------------------------------
		@param self: object pointer
		'''
		if self.out_amount:
			for rec in self:
				ser_tax = ((self.out_amount) * (float(self.tax))) / 100
				self.total = self.out_amount - ser_tax


# ============= Invoice ============== #
class account_invoice(models.Model):

	_inherit = 'account.invoice'

	@api.multi
	def confirm_paid(self):
		'''
		This method change pos orders states to done when folio invoice
		is in done.
		----------------------------------------------------------
		@param self: object pointer
		'''
		pos_order_obj = self.env['pos.order']
		res = super(account_invoice, self).confirm_paid()
		pos_ids = pos_order_obj.search([('invoice_id', '=', self._ids)])
		if pos_ids.ids:
			for pos_id in pos_ids:
				pos_id.write({'state': 'done'})
		return res