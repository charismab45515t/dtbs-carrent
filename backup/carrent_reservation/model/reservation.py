from openerp import models, fields, api, _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, ValidationError
import datetime
import time

class hotel_folio(models.Model):

	_inherit = 'dtbs.carrent.folio'
	_order = 'reservation_id desc'

	reservation_id = fields.Many2one(comodel_name='dtbs.carrent.booking', string='Reservation Id')


class Booking(models.Model):
	_name = "dtbs.carrent.booking"
	_rec_name = "name"
	_order = 'name desc'
	_inherit = ['mail.thread', 'ir.needaction_mixin']
	_description = "Booking"


	name = fields.Char(string="Reservation Number", readonly=True)
	customer_id = fields.Many2one(comodel_name="res.partner", string="Customer", readonly=True, required=True, states={'draft': [('readonly', False)]})
	date_order = fields.Date('Date Ordered', required=True, readonly=True, states={'draft': [('readonly', False)]},
									default=(lambda *a:time.strftime(DEFAULT_SERVER_DATE_FORMAT)))
	warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Rental', readonly=True, required=True, default=1, states={'draft': [('readonly', False)]})
	pricelist_id = fields.Many2one(comodel_name='product.pricelist', string='Scheme', required=True, readonly=True, states={'draft': [('readonly', False)]},
									help="Pricelist for current reservation.")
	partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Invoice Address', readonly=True, states={'draft':[('readonly', False)]},
									help="Invoice address for current reservation.")
	partner_order_id = fields.Many2one(comodel_name='res.partner', string='Ordering Contact', readonly=True, states={'draft':[('readonly', False)]},
									help="The name and address of the contact that requested the order or quotation.")
	partner_shipping_id = fields.Many2one(comodel_name='res.partner', string='Delivery Address', readonly=True, states={'draft':[('readonly', False)]},
									help="Delivery address for current reservation.")
	checkin = fields.Date(string='Expected-Date-Begin', required=True, readonly=True, states={'draft': [('readonly', False)]})
	checkout = fields.Date(string='Expected-Date-End', required=True, readonly=True, states={'draft': [('readonly', False)]})
	bookingunit_ids = fields.One2many(comodel_name="dtbs.carrent.bookingunit", inverse_name="booking_id", string="Reservation Unit",
									help='Unit reservation details.')	
	folio_id = fields.Many2many('dtbs.carrent.folio', 'dtbs_carrent_folio_reservation_rel', 'order_id', 'invoice_id', string='Folio')
	state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),('cancel', 'Cancelled'), ('done', 'Done')],
							'State', readonly=True, default=lambda *a: 'draft')


	@api.constrains('bookingunit_ids')
	def check_reservation_units(self):
		'''
		This method is used to validate the bookingunit_ids.
		-----------------------------------------------------
		@param self: object pointer
		@return: raise a warning depending on the validation
		'''
		for reservation in self:
			if len(reservation.bookingunit_ids) == 0:
				raise ValidationError('Please Select Units For Reservation.')
			for rec in reservation.bookingunit_ids:
				if len(rec.reserve) == 0:
					raise ValidationError('Please Select Units For Reservation.')


	@api.model
	def _needaction_count(self, domain=None):
		"""
		 Show a count of draft state reservations on the menu badge.
		"""
		return self.search_count([('state', '=', 'draft')])


	@api.onchange('customer_id')
	def onchange_customer_id(self):
		'''
		When you change customer_id it will update the partner_invoice_id,
		partner_shipping_id and pricelist_id of the hotel reservation as well
		---------------------------------------------------------------------
		@param self: object pointer
		'''
		if not self.customer_id:
			self.partner_invoice_id = False
			self.partner_shipping_id = False
			self.partner_order_id = False
		else:
			addr = self.customer_id.address_get(['delivery', 'invoice', 'contact'])
			self.partner_invoice_id = addr['invoice']
			self.partner_order_id = addr['contact']
			self.partner_shipping_id = addr['delivery']
			self.pricelist_id = self.customer_id.property_product_pricelist.id


	@api.multi
	def send_reservation_mail(self):
		'''
		This function opens a window to compose an email,
		template message loaded by default.
		@param self: object pointer
		'''
		assert len(self._ids) == 1, 'This is for a single id at a time.'
		ir_model_data = self.env['ir.model.data']
		try:
			template_id = (ir_model_data.get_object_reference('dtbs_carrent_booking','email_template_carrent_reservation')[1])
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

	@api.onchange('date_order', 'checkin')
	def on_change_checkin(self):
		'''
		When you change date_order or checkin it will check whether
		Checkin date should be greater than the current date
		------------------------------------------------------------
		@param self: object pointer
		@return: raise warning depending on the validation
		'''
		if self.date_order and self.checkin:
			if self.checkin < self.date_order:
				raise except_orm('Warning', 'Begin date should be greater than the order date.')

	@api.constrains('name', 'date_order', 'checkin')
	def constraint_checkin(self):
		if self.date_order and self.checkin:
			if self.checkin < self.date_order:
				raise except_orm('Warning', 'Begin date should be greater than the order date.')

	@api.onchange('checkout', 'checkin')
	def on_change_checkout(self):
		'''
		When you change checkout or checkin it will check whether
		Checkout date should be greater than Checkin date
		-----------------------------------------------------------
		@param self: object pointer
		@return: raise warning depending on the validation
		'''
		if self.checkout and self.checkin:
			if self.checkout < self.checkin:
				raise except_orm('Warning', 'End date should be greater than Begin date.')

	@api.constrains('name', 'checkout', 'checkin')
	def constraint_checkinout(self):
		if self.checkout and self.checkin:
			if self.checkout < self.checkin:
				raise except_orm('Warning', 'End date should be greater than Begin date.')

	@api.multi
	def confirmed_reservation(self):
		"""
		This method create a new recordset for hotel room reservation line
		------------------------------------------------------------------
		@param self: The object pointer
		@return: new record set for hotel room reservation line.
		"""
		reservation_line_obj = self.env['dtbs.carrent.unit.reservation.line']
		for reservation in self:
			self._cr.execute("select count(*) from dtbs_carrent_booking as hr "
							"inner join dtbs_carrent_bookingunit as hrl on hrl.booking_id = hr.id "
							"inner join carrent_reservation_unit_rel as hrlrr on hrlrr.unit_id = hrl.id "
							"where (checkin,checkout) overlaps ( timestamp %s, timestamp %s ) "
							"and hr.id <> cast(%s as integer) "
							"and hr.state = 'confirm' "
							"and hrlrr.carrent_reservation_unit_id in ("
							"select hrlrr.carrent_reservation_unit_id from dtbs_carrent_booking as hr "
							"inner join dtbs_carrent_bookingunit as hrl on hrl.booking_id = hr.id "
							"inner join carrent_reservation_unit_rel as hrlrr on hrlrr.unit_id = hrl.id "
							"where hr.id = cast(%s as integer) )",
							(reservation.checkin, reservation.checkout,
							str(reservation.id), str(reservation.id)))
			res = self._cr.fetchone()
			unitcount = res and res[0] or 0.0
			if unitcount:
				raise except_orm('Warning', 'You tried to confirm reservation with unit those already reserved in this reservation period')
			else:
				self.write({'state': 'confirm'})
				for line_id in reservation.bookingunit_ids:
					line_id = line_id.reserve
					for unit_id in line_id:
						vals = {
							'unit_id': unit_id.id,
							'check_in': reservation.checkin,
							'check_out': reservation.checkout,
							'state': 'assigned',
							'reservation_id': reservation.id,
							}
						#unit_id.write({'isvehicle': False, 'status': 'occupied'})
						reservation_line_obj.create(vals)
		return True



	@api.multi
	def cancel_reservation(self):
		carrent_booking_unit_line_obj = self.env['dtbs.carrent.unit.reservation.line']
		carrent_booking_unit_line_ids = carrent_booking_unit_line_obj.search([('reservation_id', '=', self.id)])
		for line in carrent_booking_unit_line_ids:
			line.write({'state': 'unassigned'})
		self.write({'state': 'cancel'})
		return True

	@api.multi
	def create_folio(self):
		"""
		This method is for create new hotel folio.
		-----------------------------------------
		@param self: The object pointer
		@return: new record set for hotel folio.
		"""
		rental_folio_obj = self.env['dtbs.carrent.folio']
		unit_obj = self.env['dtbs.carrent.unit']
		for reservation in self:
			folio_lines = []
			checkin_date = reservation['checkin']
			checkout_date = reservation['checkout']
			if not self.checkin < self.checkout:
				raise except_orm('Error', 'Checkout date should be greater than the Checkin date.')
			duration_vals = (self.onchange_check_dates(checkin_date=checkin_date,checkout_date=checkout_date, duration=False))
			duration = duration_vals.get('duration') or 0.0
			folio_vals = {
				'date_order': reservation.date_order,
				'warehouse_id': reservation.warehouse_id.id,
				'partner_id': reservation.customer_id.id,
				'pricelist_id': reservation.pricelist_id.id,
				'partner_invoice_id': reservation.partner_invoice_id.id,
				'partner_shipping_id': reservation.partner_shipping_id.id,
				'checkin_date': reservation.checkin,
				'checkout_date': reservation.checkout,
				'duration': duration,
				'reservation_id': reservation.id
				#'service_lines': reservation['folio_id']
			}
			date_a = (datetime.datetime(*time.strptime(reservation['checkout'],DEFAULT_SERVER_DATE_FORMAT)[:5]))
			date_b = (datetime.datetime(*time.strptime(reservation['checkin'],DEFAULT_SERVER_DATE_FORMAT)[:5]))
			for line in reservation.bookingunit_ids:
				for r in line.reserve:
					folio_lines.append((0, 0, {
						'checkin_date': checkin_date,
						'checkout_date': checkout_date,
						'product_id': r.product_id and r.product_id.id,
						'name': reservation['name'],
						'product_uom': r['uom_id'].id,
						'price_unit': r['lst_price'],
						'product_uom_qty': ((date_a - date_b).days) + 1
					}))
					res_obj = unit_obj.browse([r.id])
					#res_obj.write({'status': 'occupied', 'isvehicle': False})
			folio_vals.update({'unit_lines': folio_lines})
			folio = rental_folio_obj.create(folio_vals)
			self._cr.execute('insert into dtbs_carrent_folio_reservation_rel'
							'(order_id, invoice_id) values (%s,%s)',  (reservation.id, folio.id))
			reservation.write({'state': 'done'})
		return True


	@api.multi
	def onchange_check_dates(self, checkin_date=False, checkout_date=False, duration=False):
		'''
		This mathod gives the duration between check in checkout if
		customer will leave only for some hour it would be considers
		as a whole day. If customer will checkin checkout for more or equal
		hours, which configured in company as additional hours than it would
		be consider as full days
		--------------------------------------------------------------------
		@param self: object pointer
		@return: Duration and checkout_date
		'''
		value = {}
		company_obj = self.env['res.company']
		configured_addition_hours = 0
		company_ids = company_obj.search([])
		if company_ids.ids:
			configured_addition_hours = company_ids[0].additional_hours
		duration = 0
		if checkin_date and checkout_date:
			chkin_dt = (datetime.datetime.strptime(checkin_date, DEFAULT_SERVER_DATE_FORMAT))
			chkout_dt = (datetime.datetime.strptime(checkout_date, DEFAULT_SERVER_DATE_FORMAT))
			dur = chkout_dt - chkin_dt
			duration = dur.days + 1
			if configured_addition_hours > 0:
				additional_hours = abs((dur.seconds / 60) / 60)
				if additional_hours >= configured_addition_hours:
					duration += 1
		value.update({'duration': duration})
		return value


	def create(self, cr, uid, vals, context=None):
		if vals.get('name','/')=='/':
			vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'dtbs.carrent.booking') or '/'
		context = dict(context or {}, mail_create_nolog=True)
		order =  super(Booking, self).create(cr, uid, vals, context=context)
		return order


class Bookingunit(models.Model):
	_name = "dtbs.carrent.bookingunit"
	_description = "Reservation Unit"

	name = fields.Char('Name', size=64)
	booking_id = fields.Many2one(comodel_name="dtbs.carrent.booking")
	reserve = fields.Many2many('dtbs.carrent.unit', 'carrent_reservation_unit_rel', 'unit_id', 'carrent_reservation_unit_id', 
							domain="[('isvehicle','=',True), ('categ_id','=',categ_id)]")
	categ_id = fields.Many2one(comodel_name='product.category', string='Vehicle Category', domain="[('isvehiclecat','=',True)]",
							change_default=True)


	@api.onchange('categ_id')
	def on_change_categ(self):
		'''
		When you change categ_id it check checkin and checkout are
		filled or not if not then raise warning
		-----------------------------------------------------------
		@param self: object pointer
		'''
		carrent_unit_obj = self.env['dtbs.carrent.unit']
		carrent_unit_ids = carrent_unit_obj.search([('categ_id', '=', self.categ_id.id), ('isvehicle', '=', True)])
		assigned = False
		unit_ids = []
		if not self.booking_id.checkin:
			raise except_orm('Warning', 'Before choosing a vehicle, You have to select a Begin date or a End date in the reservation form.')
		for unit in carrent_unit_ids:
			assigned = False
			for reservation in unit.carrent_reservation_unit_ids:
				if((reservation.check_in >= self.booking_id.checkin and
					reservation.check_in <= self.booking_id.checkout or
					reservation.check_out <= self.booking_id.checkout and
					reservation.check_out >= self.booking_id.checkin) and
					reservation.reservation_id.state != 'cancel'):
					assigned = True
			if not assigned:
				unit_ids.append(unit.id)
		domain = {'reserve': [('id', 'in', unit_ids)]}
		return {'domain': domain}

	#@api.multi
	#def unlink(self):
	#	"""
	#	Overrides orm unlink method.
	#	@param self: The object pointer
	#	@return: True/False.
	#	"""
	#	carrent_unit_reserv_line_obj = self.env['dtbs.carrent.unit.reservation.line']
	#	for reserv_rec in self:
	#		for rec in reserv_rec.reserve:
	#			hres_arg = [('unit_id', '=', rec.id),
	#						('reservation_id', '=', reserv_rec.booking_id.id)]
	#			myobj = carrent_unit_reserv_line_obj.search(hres_arg)
	#			if myobj.ids:
	#				rec.write({'isvehicle': True, 'status': 'available'})
	#				myobj.unlink()
	#	return super(Bookingunit, self).unlink()


class carrent_unit_reservation_line(models.Model):
	_name = 'dtbs.carrent.unit.reservation.line'
	_description = 'Room Reservation'
	_rec_name = 'unit_id'

	unit_id = fields.Many2one(comodel_name='dtbs.carrent.unit', string='Vehicle')
	check_in = fields.Date('Begin Date', required=True)
	check_out = fields.Date('End Date', required=True)
	state = fields.Selection([('assigned', 'Assigned'), ('unassigned', 'Unassigned')], 'Vehicle Status')
	reservation_id = fields.Many2one('dtbs.carrent.booking', string='Reservation')
	status = fields.Selection(string='State', related='reservation_id.state')

carrent_unit_reservation_line()


class Unit(models.Model):
	_inherit = 'dtbs.carrent.unit'
	_description = 'Vehicle'

	carrent_reservation_unit_ids = fields.One2many(comodel_name='dtbs.carrent.unit.reservation.line', inverse_name='unit_id', string='Vehicle Reserv Line')


	@api.model
	def cron_unit_line(self):
		"""
		This method is for scheduler
		every 1min scheduler will call this method and check Status of
		unit is occupied or available
		--------------------------------------------------------------
		@param self: The object pointer
		@return: update status of unit reservation line
		"""
		for unit in self:
			status = {'isvehicle': False, 'color': 2}
			unit.write(status)

		# reservation_line_obj = self.env['dtbs.carrent.unit.reservation.line']
		# folio_unit_line_obj = self.env['dtbs.carrent.folio.unit.line']
		# now = datetime.datetime.now()
		# curr_date = now.strftime(DEFAULT_SERVER_DATE_FORMAT)
		# for unit in self.search([]):
		# 	reserv_line_ids = [reservation_line.ids for reservation_line in unit.unit_reservation_line_ids]
		# 	reserv_args = [('id', 'in', reserv_line_ids), ('check_in', '<=', curr_date), ('check_out', '>=', curr_date)]
		# 	reservation_line_ids = reservation_line_obj.search(reserv_args)
		# 	units_ids = [unit_line.ids for unit_line in unit.unit_line_ids]
		# 	rom_args = [('id', 'in', units_ids), ('check_in', '<=', curr_date), ('check_out', '>=', curr_date)]
		# 	unit_line_ids = folio_unit_line_obj.search(rom_args)
		# 	status = {'isvehicle': True, 'color': 5}
		# 	if reservation_line_ids.ids:
		# 		status = {'isvehicle': False, 'color': 2}
		# 	unit.write(status)
		# 	if unit_line_ids.ids:
		# 		status = {'isvehicle': False, 'color': 2}
		# 	unit.write(status)

		# 	if reservation_line_ids.ids and unit_line_ids.ids:
		# 		raise except_orm(_('Wrong Entry'), _('Please Check Units Status for %s.' % (unit.name)))
		return True


class Reservationsummary(models.Model):

	_name = 'dtbs.carrent.reservation.summary'
	_description = 'Unit reservation summary'

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
		res = super(Reservationsummary, self).default_get(fields)
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
		reservation_line_obj = self.env['dtbs.carrent.unit.reservation.line']
		date_range_list = []
		main_header = []
		summary_header_list = ['Units']
		if self.date_from and self.date_to:
			if self.date_from > self.date_to:
				raise except_orm('User Error!', 'Please Check Time period Date From can\'t be greater than Date To !')
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
				if not unit.carrent_reservation_unit_ids:
					raise ValidationError('1')
					for chk_date in date_range_list:
						unit_list_stats.append({'state': 'Free', 'date': chk_date})
				else:
					for chk_date in date_range_list:
						for unit_res_line in unit.carrent_reservation_unit_ids:
							reservline_ids = [i.ids for i in unit.carrent_reservation_unit_ids]
							reservline_ids = (reservation_line_obj.search
												([('id', 'in', reservline_ids),
												('check_in', '<=', chk_date),
												('check_out', '>=', chk_date)
												]))
							if reservline_ids:
								unit_list_stats.append({'state': 'Reserved',
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