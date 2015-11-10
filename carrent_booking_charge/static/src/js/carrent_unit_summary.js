 openerp.carrent_booking = function(openerp) {
    var _t = openerp.web._t;
    _lt = openerp.web._lt;
    var QWeb = openerp.web.qweb;
    
    console.log("asdasdasdasdasdas");
    openerp.carrent_booking.UnitSummary = openerp.web.form.FormWidget.extend(openerp.web.form.ReinitializeWidgetMixin, {
    	
    	display_name: _lt('Form'),
        view_type: "form",
        
        init: function() {
            this._super.apply(this, arguments);
	    	if(this.field_manager.model == "dtbs.carrent.booking.summary")
	    	{
	    		$(".oe_view_manager_buttons").hide();
	    		$(".oe_view_manager_header").hide();
	   		}
            this.set({
                date_to: false,
                date_from: false,
                summary_header: false,
                unit_summary: false,
            });
            this.summary_header = [];
            this.unit_summary = [];
            this.field_manager.on("field_changed:date_from", this, function() {
                this.set({"date_from": openerp.web.str_to_date(this.field_manager.get_field_value("date_from"))});
            });
            this.field_manager.on("field_changed:date_to", this, function() {
                this.set({"date_to": openerp.web.str_to_date(this.field_manager.get_field_value("date_to"))});
            });
            
            this.field_manager.on("field_changed:summary_header", this, function() {
                this.set({"summary_header": this.field_manager.get_field_value("summary_header")});
            });
            this.field_manager.on("field_changed:unit_summary", this, function() {
                this.set({"unit_summary":this.field_manager.get_field_value("unit_summary")});
            });
            
        },
        
        initialize_field: function() {
            openerp.web.form.ReinitializeWidgetMixin.initialize_field.call(this);
            var self = this;
            self.on("change:summary_header", self, self.initialize_content);
            self.on("change:unit_summary", self, self.initialize_content);
        },
        
      initialize_content: function() {
    	   var self = this;
           if (self.setting)
               return;
           
           if (!this.summary_header || !this.unit_summary)
              	return
           // don't render anything until we have summary_header and unit_summary
              	
           this.destroy_content();
           
           if (this.get("summary_header")) {
            this.summary_header = py.eval(this.get("summary_header"));
           }
           if (this.get("unit_summary")) {
            this.unit_summary = py.eval(this.get("unit_summary"));
           }
           	
           this.renderElement();
           this.view_loading();
        },
        
        view_loading: function(r) {
            return this.load_form(r);
        },
        
        load_form: function(data) {
            self.action_manager = new openerp.web.ActionManager(self);
            
            this.$el.find(".table_free").bind("click", function(event){
                self.action_manager.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'dtbs.carrent.booking',
                        views: [[false, 'form']],
                        target: 'new',
                        context: {'unit_id': $(this).attr('data'), 'date_rent': $(this).attr('date')},
                });
            });
        
        },
       
        renderElement: function() {
             this.destroy_content();
             this.$el.html(QWeb.render("summaryDetails", {widget: this}));
        }     
    });

    openerp.web.form.custom_widgets.add('Unit_Booking', 'openerp.carrent_booking.UnitSummary');
};

