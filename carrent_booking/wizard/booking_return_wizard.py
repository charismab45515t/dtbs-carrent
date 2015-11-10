from openerp import models, fields, api
from openerp.tools import misc, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, Warning, ValidationError
from decimal import Decimal
import datetime
import time
import urllib2

class booking_return_wizard(models.TransientModel):
	_name = 'dtbs.carrent.return.wizard'
	_description = 'Booking Return Wizard'

	date_return = fields.Date(string="Date Return", required=True, default=(lambda *a:time.strftime(DEFAULT_SERVER_DATE_FORMAT)))

	@api.one
	def return_unit(self):
		active_id = self._context['active_id']
		booking = self.env['dtbs.carrent.booking'].browse(active_id)
		val = {'date_return': self.date_return}

		for record in booking:
			record.write(val)
			record.signal_workflow('return')