from openerp import models, fields, api, _, netsvc
from openerp.tools import misc, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, ValidationError
from decimal import Decimal
import datetime
import time
import urllib2


# ============= BPKB ===========================#
class bpkbunit(models.Model):
	_inherit = "dtbs.carrent.unit"

	bpkb_id = fields.Many2one(comodel_name="dtbs.carrent.bpkb", string="PMVO Number (BPKB)")
	stnk_id = fields.Many2one(comodel_name="dtbs.carrent.stnk", string="VRC Number (STNK)")

class bpkb(models.Model):
	_name = "dtbs.carrent.bpkb"
	_rec_name = "name"
	_description = "BPKB"

	name = fields.Char(string="PMVO Number (BPKB)", required=True)
	owner_name = fields.Char(string="Owner Name")
	address = fields.Char(string="Address")
	job = fields.Char(string="Job")
	police = fields.Many2one(comodel_name="dtbs.carrent.unit", string="Police Number")
	brand_id = fields.Many2one(comodel_name="dtbs.carrent.brand", string="Brand")
	car_type = fields.Char(string="Type")
	car_kind = fields.Char(string="Kind")
	model_id = fields.Many2one(comodel_name="dtbs.carrent.model", string="Model")
	create_year = fields.Integer(string="Created (Year)")
	assembly_year = fields.Integer(string="Assembly (Year)")
	silinder = fields.Char(string="Silinder")
	color_id = fields.Many2one(comodel_name="dtbs.carrent.color", string="Color")
	chassis = fields.Char(string="Chassis Number")
	machine = fields.Char(string="Machine Number")
	axes = fields.Integer(string="The number of axes")
	wheels  = fields.Integer(string="The number of wheels")
	fuel = fields.Char(string="Fuel")
	cetificate_test = fields.Char(string="Type test certificate number")
	period_test = fields.Char(string="Periodically test number")

	_sql_constraints = [
		("Unique Number", "UNIQUE(name)", "The Proof of Motorized Vehicle Ownership must be unique"),
		("Unique Police", "UNIQUE(police)", "The police number must be unique"),
	]

# ============== STNK ============== #

class stnk(models.Model):
	_name = "dtbs.carrent.stnk"
	_rec_name = "name"	
	_description = "STNK"

	name = fields.Char(string="VRC Number (STNK)", required=True)
	police = fields.Many2one(comodel_name="dtbs.carrent.unit", string="Police Number")
	applies_to = fields.Date(string="Applies To")

	_sql_constraints = [
		("Unique Number", "UNIQUE(name)", "The Proof of Vehicle Registration Cards must be unique"),
		("Unique Police", "UNIQUE(police)", "The police number must be unique"),
	]

# ============== PERPANJANGAN ============== #

class renewal(models.Model):
	_name = "dtbs.carrent.stnk.renewal"
	_description = "Perpanjangan STNK"
	_rec_name = "no_fak"
	_inherit = ['mail.thread', 'ir.needaction_mixin']
	_mail_post_access = 'read'
	_track = {
		'state': {
			'carrent_ownership.mt_renewal_new': lambda self, cr, uid, obj, ctx=None: obj.state == 'draft',
			'carrent_ownership.mt_renewal_stage': lambda self, cr, uid, obj, ctx=None: obj.state != 'draft',
		},
	}

	no_fak = fields.Char(string="Renewal Number", readonly=True)
	vrc_id = fields.Many2one(comodel_name="dtbs.carrent.stnk", string="VRC Number", required=True, track_visibility='onchange')
	state = fields.Selection([('draft', 'Draft'),('confirm', 'Confirm'),('process', 'On Process'),('cancel', 'Cancelled'),('done', 'Done')], string='Status', default='draft',
								track_visibility='onchange')
	police = fields.Char(compute="_get_police", string="Police Number", store=True)
	date_process = fields.Date(string="Processed On", required=True, default=(lambda *a:time.strftime(DEFAULT_SERVER_DATE_FORMAT)), track_visibility='onchange')
	by = fields.Char(string="Processed By", required=True, track_visibility='onchange')
	expense = fields.Float(string="Total Expenditures")
	due = fields.Date(string="Next Due Date")

	_sql_constraints = [
		("Unique Number", "UNIQUE(no_fak)", "The Renewal Number must be unique"),
	]

	@api.depends('vrc_id')
	def _get_police(self):
		police_obj = self.env['dtbs.carrent.stnk']
		police_ids = police_obj.search([('id', '=', self.vrc_id.id)])
		for vrc in police_ids:
			self.police = vrc.police.police

	@api.multi
	def confirmed_renewal(self):
		self.write({'state': 'confirm'})
		return True

	@api.multi
	def processed_renewal(self):
		self.write({'state': 'process'})
		return True

	@api.multi
	def cancelled_renewal(self):
		self.write({'state': 'cancel'})
		return True

	@api.multi
	def done_renewal(self):
		stnk_obj = self.env['dtbs.carrent.stnk']
		stnk_ids = stnk_obj.search([('id', '=', self.vrc_id.id)])
		for stnk in stnk_ids:
			stnk.write({'applies_to': self.due})

		self.write({'state': 'done'})
		return True


	def create(self, cr, uid, vals, context=None):
		# auto number
		if vals.get('no_fak','/')=='/':
			vals['no_fak'] = self.pool.get('ir.sequence').get(cr, uid, 'dtbs.carrent.stnk.renewal') or '/'
		context = dict(context or {}, mail_create_nolog=True)
		renew =  super(renewal, self).create(cr, uid, vals, context=context)
		return renew