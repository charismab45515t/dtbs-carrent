from openerp import models, fields, api, netsvc
from openerp.tools import misc, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, ValidationError
from decimal import Decimal
from ..text import AVAILABLE, OCCUPIED, UNIQ_CODE, UNIQ_POLICE
import datetime
import time
import urllib2

STATE = (
    ('available', AVAILABLE),
    ('occupied', OCCUPIED),
)

# =========  Brand =========== #
class Brand(models.Model):
	_name = "dtbs.carrent.brand"
	_description = "Brand"

	name = fields.Char("Name", required=True)

# =========  Model =========== #
class Model(models.Model):
	_name = "dtbs.carrent.model"
	_description = "Model"

	name = fields.Char("Name", required=True)
	brand = fields.Many2one(comodel_name="dtbs.carrent.brand",string="Brand", required=True)


# =========  Color =========== #
class Color(models.Model):
	_name = "dtbs.carrent.color"
	_description = "Color"

	name = fields.Char("Color", required=True)


# ========= Categories ============ #
class product_category(models.Model):
	_inherit = "product.category"

	isvehiclecat = fields.Boolean('Is Vehicle Category')

class Category(models.Model):
	_name = "dtbs.carrent.category"
	_description = "Category"

	cat_id = fields.Many2one(comodel_name="product.category", string="Category", required=True, delegate=True, select=True, ondelete='cascade')
	cat_parent_id = fields.Many2one(comodel_name="dtbs.carrent.category", string='Vehicles Parent Category', select=True, ondelete='cascade')
	cat_child_id = fields.One2many(comodel_name="dtbs.carrent.category", inverse_name="cat_parent_id", string='Vehicles Child Categories')

	@api.onchange('parent_id')
	def parent_id_change(self):
		for record in self:
			record.cat_parent_id = record.env['dtbs.carrent.category'].search([('cat_id', '=', record.parent_id.id)]).id



# ========= Amenity ============= #
class Facility(models.Model):
	_name = "dtbs.carrent.facility"
	_description = "Facility"

	name = fields.Char(string="Facility", required=True)
	desc = fields.Text(string="Description")


# ============ Unit ==============#
 
class product_template(models.Model):
	_inherit = "product.template"

	isvehicle = fields.Boolean('Is Available', default=True)


class Unit(models.Model):
	_name = "dtbs.carrent.unit"
	_rec_name = "product_id"
	_description = "Vehicle"

	product_id = fields.Many2one(comodel_name='product.template', string='Product_id', required=True, delegate=True, ondelete='cascade')

	code = fields.Char(string="Vehicle Code", required=True)
	police = fields.Char(string="Police Number", required=True)
	brand_id = fields.Many2one(comodel_name="dtbs.carrent.brand", string="Brand", required=True)
	color = fields.Many2one(comodel_name="dtbs.carrent.color", string="Color")
	capacity = fields.Integer(string="Capacity")
	year = fields.Integer(string="Production Year")
	desc = fields.Text(string="Description")
	facility_ids = fields.Many2many(comodel_name="dtbs.carrent.facility", string="Facility")
	model_id = fields.Many2one(comodel_name="dtbs.carrent.model", string="Model", required=True)
	status = fields.Selection(STATE, string='Current Status', default='available')
	kanban_color = fields.Integer()
	fuel = fields.Char(string="Fuel")



	_sql_constraints = [
		("Unique Code", "UNIQUE(code)", UNIQ_CODE),
		("Unique Police", "UNIQUE(police)", UNIQ_POLICE),
	]

	@api.onchange('uom_id')
	def uom_change(self):
		uom_categ = self.env['product.uom']
		uom_categ_ids = uom_categ.search([('id', '=', self.uom_id.id)])
		for x in uom_categ_ids:
			self.uom_category_id = x.category_id


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