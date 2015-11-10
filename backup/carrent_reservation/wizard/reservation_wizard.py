from openerp import models, fields, api


class make_folio_wizard(models.TransientModel):

    _name = 'dtbs.carrent.wizard.make.folio'

    grouped = fields.Boolean('Group the Folios')

    @api.multi
    def makeFolios(self):
        order_obj = self.env['dtbs.carrent.booking']
        newinv = []
        for order in order_obj.browse(self._context['active_ids']):
            for folio in order.folio_id:
                newinv.append(folio.id)
        return {
            'domain': "[('id','in', [" + ','.join(map(str, newinv)) + "])]",
            'name': 'Folios',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'dtbs.carrent.folio',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
