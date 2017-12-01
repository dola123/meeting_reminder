openerp.meeting_reminder = function(instance){
    var QWeb = instance.web.qweb;
    var _t = instance.web._t,
        _lt = instance.web._lt;

    instance.web_calendar.QuickCreate.include({
        slow_create: function(data) {
            //if all day, we could reset time to display 00:00:00
            var self = this;
            var def = $.Deferred();
            var defaults = {};
            var created = false;

            _.each($.extend({}, this.data_template, data), function(val, field_name) {
                defaults['default_' + field_name] = val;
            });
                        
            var pop_infos = self.get_form_popup_infos();
            var pop = new instance.web.form.FormOpenPopup(this);
            var context = new instance.web.CompoundContext(this.dataset.context, defaults);
            pop.show_element(this.dataset.model, null, this.dataset.get_context(defaults), {
                title: this.get_title(),
                disable_multiple_selection: true,
                view_id: pop_infos.view_id,
                // Ensuring we use ``self.dataset`` and DO NOT create a new one.
                create_function: function(data, options) {
                      return self.dataset.create(data, options).done(function(r) {
                          if(self.dataset.model == 'calendar.event'){
                              var id = r;
                              var calendar_event_details = [];
                              var weekday = new Array(7);
                              weekday[0]=  _t("Sunday");
                              weekday[1] = _t("Monday");
                              weekday[2] = _t("Tuesday");
                              weekday[3] = _t("Wednesday");
                              weekday[4] = _t("Thursday");
                              weekday[5] = _t("Friday");
                              weekday[6] = _t("Saturday");
                              self.dataset.call('get_event_details',[[id]]).done(function(recurrent_ids){
                                  _.each(recurrent_ids[0],function(recurrent_id){
                                      if(recurrent_id.toString().search('-') != -1){
                                          var recurrent_date_time = recurrent_id.split('-')[1]
                                          var year = recurrent_date_time.substr(0,4);
                                          var month =  recurrent_date_time.substr(4,2);
                                          var day = recurrent_date_time.substr(6,2);
                                          var hours = recurrent_date_time.substr(8,2);
                                          var minutes = recurrent_date_time.substr(10,2);
                                          var seconds = recurrent_date_time.substr(12,2);
                                          var date = instance.web.format_value( new Date(parseInt(year),(parseInt(month)-1),parseInt(day)), {"widget": 'date'})
                                          if(data.start_datetime){
                                              date_time = year + "-" + month + "-" + day +" " + hours + ":" + minutes + ":" + seconds;
                                              date = instance.web.format_value( instance.web.str_to_datetime(date_time), {"widget": 'datetime'})
                                          }
                                          calendar_event_details.push({
                                              'name':data.name,
                                              'date':date,
                                              'location':data.location,
                                              'show_as':data.show_as,
                                              'class':data['class'],
                                              'duration':recurrent_ids[1].duration,
                                              'user_name':recurrent_ids[1].user_name,
                                              'week_name': weekday[new Date(date).getDay()],
                                          })
                                      }else{
                                          var date = instance.web.format_value( data.start_date, {"widget": 'date'})
                                          if(data.start_datetime){
                                              date = instance.web.format_value( instance.web.str_to_datetime(data.start_datetime), {"widget": 'datetime'})
                                          }
                                          console.log("56565656",date,new Date(date), weekday[new Date(date).getDay()])
                                          calendar_event_details.push({
                                              'name':data.name,
                                              'date':date,
                                              'location':data.location,
                                              'show_as':data.show_as,
                                              'class':data['class'],
                                              'duration':recurrent_ids[1].duration,
                                              'user_name':recurrent_ids[1].user_name,
                                              'week_name': weekday[new Date(date).getDay()],
                                          })
                                      }
                                  })
                                  self.displayEvent = $(QWeb.render("DisplayEvent", {'widget': self,'calendar_event_details':calendar_event_details})).dialog({
                                      resizable: false,
                                      height:400,
                                      width:650,
                                      title: _t("Display Event"),
                                      position: "center",
                                      modal : true,
                                      open : function(){
                                          $('.ui-dialog-buttonpane').find('button:contains("Ok")').addClass('alert_dialog_button');
                                          $('.ui-dialog-buttonpane').find('button:contains("Close")').addClass('alert_dialog_button');
                                      },
                                      close: function( event, ui ) {
                                          $( this ).remove();
                                          self.dataset.unlink(id)
                                          $(".oe_vm_switch_calendar").click();
                                          var newdata = _.omit(data,'message_follower_ids')
                                          self.slow_create(newdata);
                                      },
                                      buttons: {
                                          "Ok": function() {
                                              $( this ).remove()
                                          },
                                          "Close": function() {
                                              $( this ).remove()
                                              self.dataset.unlink(id);
                                              $(".oe_vm_switch_calendar").click();
                                              var newdata = _.omit(data,'message_follower_ids')
                                              self.slow_create(newdata);
                                          }
                                      },
                                  })
                              })
                          }
                       }).fail(function (r, event) {
                           if (!r.data.message) { //else manage by openerp
                               throw new Error(r);
                           }
                       });
                },
                read_function: function(id, fields, options) {
                    return self.dataset.read_ids.apply(self.dataset, arguments).done(function() {
                    }).fail(function (r, event) {
                        if (!r.data.message) { //else manage by openerp
                            throw new Error(r);
                        }
                    });
                },
            });
            pop.on('closed', self, function() {
                // ``self.trigger('close')`` would itself destroy all child element including
                // the slow create popup, which would then re-trigger recursively the 'closed' signal.  
                // Thus, here, we use a deferred and its state to cut the endless recurrence.
                if (def.state() === "pending") {
                    def.resolve();
                }
            });
            pop.on('create_completed', self, function(id) {
                created = true;
                self.trigger('slowadded');
            });
            def.then(function() {
                if (created) {
                    var parent = self.getParent();
                    if(self.$calendar != undefined){
                        parent = self.$calendar
                    }else{
                        self.$calendar = parent
                    }
                    parent.$calendar.fullCalendar('refetchEvents');
                }
                self.trigger('close');
            });
            return def;
        },
    });

    function zero_pad(num,size){
        var s = ""+num;
        while (s.length < size) {
            s = "0" + s;
        }
        return s;
    }

    instance.web_calendar.CalendarView.include({

        holiday : function(records){
            _.each(records,function(record){
                var start = new Date(record.start_date);
                var end = false;
                if(record.stop_date){
                    end = new Date(record.stop_date); 
                }else{
                    $(".fc-day[data-date="+record.start_date+"]").css('background',record.color);;
                    $(".fc-day[data-date="+record.start_date+"]").find('.fc-day-number').after("<span style='word-break: break-all;'>"+record.name+"</span>")
                }
                if(start && end){
                    while(start <= end){
                        var year = start.getFullYear();
                        var month= start.getMonth() + 1;
                        var day = start.getDate();
                        var date = year + "-" + zero_pad(month,2) + "-" +zero_pad(day,2);
                        $(".fc-day[data-date="+date.trim('')+"]").css('background',record.color);
                        $(".fc-day[data-date="+date.trim('')+"]").find('.fc-day-number').after("<span style='word-break: break-all;'>"+record.name+"</span>")
                        var newDate = start.setDate(start.getDate() + 1);
                        start = new Date(newDate);
                     }
                }
           })
        },

        view_loading: function (fv) {
            var self = this;
            this._super(fv)
            if(self.model && self.model == 'calendar.event'){
                self.holiday_master_dataset = new instance.web.DataSetSearch(self, 'holiday.master', {}, []);
                self.holiday_master_dataset.read_slice(['start_date','stop_date','name','color'], {}).then(function(records){
                    self.records = records;
                    self.holiday(self.records);
                    $(".fc-button").click(function(){
                        self.holiday(self.records);
                    });
                });
            }
        },

    });

}