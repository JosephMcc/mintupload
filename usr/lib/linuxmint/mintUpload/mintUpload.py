#!/usr/bin/env python

# mintUpload
#	Clement Lefebvre <root@linuxmint.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; Version 3
# of the License.



import sys

try:
	import pygtk
	pygtk.require("2.0")
except:
	pass

try:
	import gtk
	import gtk.glade
	import os
	import gettext
	import commands
	from mintUploadCore import *
except Exception as e:
	print "You do not have all the dependencies!"
	print str(e)
	sys.exit(1)



gtk.gdk.threads_init()
__version__ = VERSION
# i18n
gettext.install("messages", "/usr/lib/linuxmint/mintUpload/locale")



class gtkErrorObserver:
	'''All custom defined errors, using the statusbar'''

	def __init__(self, statusbar):
		self.statusbar = statusbar

	def error(self, err):
		context_id = self.statusbar.get_context_id("mintUpload")
		message = "<span color='red'>" + err.summary + "</span>"
		self.statusbar.push(context_id, message)
		self.statusbar.get_children()[0].get_children()[0].set_use_markup(True)



class gtkSpaceChecker(mintSpaceChecker):
	'''Checks for available space on the service'''

	def __init__(self, service, filesize, statusbar, wTree):
		mintSpaceChecker.__init__(self, service, filesize)
		self.statusbar = statusbar
		self.wTree = wTree

	def run(self):
		context_id = self.statusbar.get_context_id("mintUpload")

		# Get the file's persistence on the service
		if self.service.has_key('persistence'):
			self.wTree.get_widget("txt_persistence").set_label(str(self.service['persistence']) + " " + _("days"))
			self.wTree.get_widget("txt_persistence").show()
			self.wTree.get_widget("lbl_persistence").show()
		else:
			self.wTree.get_widget("txt_persistence").set_label(_("N/A"))
			self.wTree.get_widget("txt_persistence").hide()
			self.wTree.get_widget("lbl_persistence").hide()

		# Get the maximum allowed filesize on the service
		if self.service.has_key('maxsize'):
			maxsizeStr = sizeStr(self.service['maxsize'])
			self.wTree.get_widget("txt_maxsize").set_label(maxsizeStr)
			self.wTree.get_widget("txt_maxsize").show()
			self.wTree.get_widget("lbl_maxsize").show()
		else:
			self.wTree.get_widget("txt_maxsize").set_label(_("N/A"))
			self.wTree.get_widget("txt_maxsize").hide()
			self.wTree.get_widget("lbl_maxsize").hide()

		needsCheck = True
		if not self.service.has_key('space'):
			self.wTree.get_widget("txt_space").set_label(_("N/A"))
			self.wTree.get_widget("txt_space").hide()
			self.wTree.get_widget("lbl_space").hide()
			if not self.service.has_key('maxsize'):
				needsCheck=False
				# Activate upload button
				self.statusbar.push(context_id, "<span color='green'>" + _("Service ready. Space available.") + "</span>")
				label = self.statusbar.get_children()[0].get_children()[0]
				label.set_use_markup(True)
				self.wTree.get_widget("upload_button").set_sensitive(True)

		if needsCheck:
			self.wTree.get_widget("main_window").window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
			self.wTree.get_widget("combo").set_sensitive(False)
			self.wTree.get_widget("upload_button").set_sensitive(False)
			self.statusbar.push(context_id, _("Checking space on the service..."))

			self.wTree.get_widget("frame_progress").hide()

			# Check the filesize
			try:
				self.check()

			except ConnectionError: pass # already reported
			except FilesizeError:   self.display_space()

			else:
				self.display_space()
				self.statusbar.push(context_id, "<span color='green'>" + _("Service ready. Space available.") + "</span>")
				self.wTree.get_widget("upload_button").set_sensitive(True)

			finally:
				label = self.statusbar.get_children()[0].get_children()[0]
				label.set_use_markup(True)
				self.wTree.get_widget("combo").set_sensitive(True)
				self.wTree.get_widget("main_window").window.set_cursor(None)
				self.wTree.get_widget("main_window").resize(*self.wTree.get_widget("main_window").size_request())

	def display_space(self):
		'''Display the available space left on the service'''
		try:    pctSpace = float(self.available) / float(self.total) * 100
		except: pass
		else:
			pctSpaceStr = sizeStr(self.available) + " (" + str(int(pctSpace)) + "%)"
			self.wTree.get_widget("txt_space").set_label(pctSpaceStr)
			self.wTree.get_widget("txt_space").show()
			self.wTree.get_widget("lbl_space").show()



class gtkUploader(mintUploader):
	'''Wrapper for the gtk management of mintUploader'''

	def __init__(self, service, files, progressbar, statusbar, wTree):
		mintUploader.__init__(self, service, files)
		self.progressbar = progressbar
		self.statusbar = statusbar
		self.wTree = wTree

	def run(self):
		self.wTree.get_widget("upload_button").set_sensitive(False)
		self.wTree.get_widget("combo").set_sensitive(False)
		self.wTree.get_widget("main_window").window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
		self.wTree.get_widget("frame_progress").show()

		for f in self.files:
			self.wTree.get_widget("label190").show()
			self.progressbar.show()
			try:
				self.upload(f)
			except Exception as e:
				try:    raise CustomError(_("Upload failed."), e)
				except: pass

		self.wTree.get_widget("main_window").window.set_cursor(None)

	def progress(self, message, color=None):
		context_id = self.statusbar.get_context_id("mintUpload")
		mintUploader.progress(self, message)
		if color:
			color_message = "<span color='%s'>%s</span>" % (color, message)
			self.statusbar.push(context_id, color_message)
			self.statusbar.get_children()[0].get_children()[0].set_use_markup(True)
		else:
			self.statusbar.push(context_id, message)

	def pct(self, so_far, total=None):
		self.focused = self.wTree.get_widget("main_window").has_toplevel_focus()
		pct = mintUploader.pct(self, so_far, total)
		self.progressbar.set_fraction(float(pct)/100)
		self.progressbar.set_text(str(pct) + "%")

	def success(self):
		mintUploader.success(self)
		#If necessary, show the URL
		if self.service.has_key('url'):
			self.wTree.get_widget("txt_url").set_text(self.url)
			self.progressbar.hide()
			self.wTree.get_widget("label190").hide()
			self.wTree.get_widget("txt_url").show()
			self.wTree.get_widget("lbl_url").show()

			# Autocopy URL
			if config['clipboard']['autocopy'] == "True":
				# If when_unfocused is true OR window has focus
				if config['clipboard']['when_unfocused'] == "True" or self.wTree.get_widget("main_window").has_toplevel_focus():
					try:  gtk.Clipboard().set_text(self.url)
					except Exception as e:
						try:    raise CustomError(_("Could not copy URL to clipboard"), e)
						except: pass
					else: self.progress(_("Copied URL to clipboard"))

		# Report success
		self.progress(_("File uploaded successfully."), "green")



class mintUploadWindow:
	"""This is the main class for the application"""

	def __init__(self, filenames):
		self.filenames = filenames
		self.iconfile = ICONFILE

		# Set the Glade file
		self.gladefile = "/usr/lib/linuxmint/mintUpload/mintUpload.glade"
		self.wTree = gtk.glade.XML(self.gladefile,"main_window")

		self.wTree.get_widget("main_window").connect("destroy", gtk.main_quit)
		self.wTree.get_widget("main_window").set_icon_from_file(self.iconfile)
		self.wTree.get_widget("main_window").set_title(menuName)

		# i18n
		self.wTree.get_widget("label2").set_label("<b>" + _("Upload service") + "</b>")
		self.wTree.get_widget("label3").set_label("<b>" + _("Local file") + "</b>")
		self.wTree.get_widget("label4").set_label("<b>" + _("Remote file") + "</b>")
		self.wTree.get_widget("label187").set_label(_("Name:"))
		self.wTree.get_widget("lbl_space").set_label(_("Free space:"))
		self.wTree.get_widget("lbl_maxsize").set_label(_("Max file size:"))
		self.wTree.get_widget("lbl_persistence").set_label(_("Persistence:"))
		self.wTree.get_widget("label195").set_label(_("Path:"))
		self.wTree.get_widget("label193").set_label(_("Size:"))
		self.wTree.get_widget("label190").set_label(_("Upload progress:"))
		self.wTree.get_widget("lbl_url").set_label(_("URL:"))
		self.wTree.get_widget("label1").set_label(_("_Upload"))

		self.create_menubar(self.wTree.get_widget("main_window"), self.wTree.get_widget("menubar1"))
		self.reload_services(self.wTree.get_widget("combo"))

		cell = gtk.CellRendererText()
		self.wTree.get_widget("combo").pack_start(cell)
		self.wTree.get_widget("combo").add_attribute(cell,'text',0)

		self.wTree.get_widget("combo").connect("changed", self.comboChanged)
		self.wTree.get_widget("upload_button").connect("clicked", self.upload)

		self.statusbar = self.wTree.get_widget("statusbar")
		self.progressbar = self.wTree.get_widget("progressbar")

		CustomError.addObserver(gtkErrorObserver(self.statusbar))

		self.selected_service = {}
		# If service autoselect is enabled, use it
		autoselect = config['autoupload']['autoselect']
		if autoselect != "False":
			model = self.wTree.get_widget("combo").get_model()
			for i in range(len(model)):
				if model[i][0] == autoselect:
					self.wTree.get_widget("combo").set_active(i)
					self.comboChanged(None)

		# If only one service is present, autoselect it
		if len(self.services) == 1:
			self.wTree.get_widget("combo").set_active(0)
			self.comboChanged(None)
		self.refresh()

		#drag n drop
		self.wTree.get_widget("main_window").connect( "drag_data_received", self.handle_drop )
		toButton = [ ( "text/uri-list", 0, 80 ) ]
		self.wTree.get_widget("main_window").drag_dest_set( gtk.DEST_DEFAULT_MOTION |gtk.DEST_DEFAULT_HIGHLIGHT |gtk.DEST_DEFAULT_DROP, toButton, gtk.gdk.ACTION_COPY )
	
	def create_menubar(self, window, menubar):
		# Setup shortcuts
		agr = gtk.AccelGroup()
		window.add_accel_group(agr)

		# File menu
		filemenu = gtk.Menu()
		filem = gtk.MenuItem(_("_File"))
		filem.set_submenu(filemenu)

		open = gtk.ImageMenuItem(gtk.STOCK_OPEN, agr)
		open.get_child().set_text(_("Open..."))
		key, mod = gtk.accelerator_parse(_("O"))
		open.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
		open.connect("activate", self.menu_file_open)
		filemenu.append(open)

		quit = gtk.ImageMenuItem(gtk.STOCK_QUIT, agr)
		quit.get_child().set_text(_("Quit"))
		key, mod = gtk.accelerator_parse(_("Q"))
		quit.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
		quit.connect("activate", gtk.main_quit)
		filemenu.append(quit)

		menubar.append(filem)

		# Edit menu
		editMenu = gtk.MenuItem(_("_Edit"))
		editSubmenu = gtk.Menu()
		editMenu.set_submenu(editSubmenu)
		prefsMenuItem = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
		prefsMenuItem.get_child().set_text(_("Services"))
		prefsMenuItem.connect("activate", self.menu_edit_services, self.wTree.get_widget("combo"))
		editSubmenu.append(prefsMenuItem)

		menubar.append(editMenu)

		# Help menu
		helpMenu = gtk.MenuItem(_("_Help"))
		helpSubmenu = gtk.Menu()
		helpMenu.set_submenu(helpSubmenu)
		aboutMenuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
		aboutMenuItem.get_child().set_text(_("About"))
		aboutMenuItem.connect("activate", self.menu_help_about)
		helpSubmenu.append(aboutMenuItem)

		menubar.append(helpMenu)
		menubar.show_all()

	def refresh(self):
		'''updates the GUI'''
		# Print the name of the file in the GUI
		labeltext = ""
		for onefile in self.filenames:
			labeltext += onefile + "\n"
		labeltext = labeltext[:-1] #remove last \n
		self.wTree.get_widget("txt_file").set_label(labeltext)

		# Calculate the size of the file
		self.filesize = 0
		for onefile in self.filenames:
			self.filesize += os.path.getsize(onefile)
		self.wTree.get_widget("txt_size").set_label(sizeStr(self.filesize))

		if self.selected_service and self.filenames:
			checker = gtkSpaceChecker(self.selected_service, self.filesize, self.statusbar, self.wTree)
			checker.start()

	def reload_services(self, combo):
		model = gtk.TreeStore(str)
		combo.set_model(model)
		self.services = read_services()
		for service in self.services:
			iter = model.insert_before(None, None)
			model.set_value(iter, 0, service['name'])
		del model

	def menu_help_about(self, widget):
		dlg = gtk.AboutDialog()
		dlg.set_title(_("About") + " - mintUpload")
		dlg.set_version(__version__)
		dlg.set_program_name("mintUpload")
		dlg.set_comments(menuName)
		try:
			dlg.set_license(open('/usr/share/common-licenses/GPL').read())
		except Exception as e:
			try:    raise CustomError(_('Could not find GPL'), e)
			except: pass

		dlg.set_authors([
			"Clement Lefebvre <root@linuxmint.com>",
			"Philip Morrell <mintupload.emorrp1@mamber.net>",
			"Manuel Sandoval <manuel@slashvar.com>",
			"Dennis Schwertel <s@digitalkultur.net>"
		])
		dlg.set_icon_from_file(self.iconfile)
		dlg.set_logo(gtk.gdk.pixbuf_new_from_file(self.iconfile))
		def close(w, res):
		    if res == gtk.RESPONSE_CANCEL:
		        w.hide()
		dlg.connect("response", close)
		dlg.show()

	def menu_edit_services(self, widget, combo):
		servicesWindow(self.gladefile, self.iconfile, self, combo)
	
	def menu_file_open(self, widget):
		chooser = gtk.FileChooserDialog(title=None, action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		chooser.set_current_folder(home)
		chooser.set_select_multiple(True)
		chooser.set_default_response(gtk.RESPONSE_OK)

		response = chooser.run()
		if response == gtk.RESPONSE_OK:
			for file in chooser.get_filenames():
				if not file in self.filenames:
					self.filenames.append(file)
			self.refresh()

		chooser.destroy()

	def comboChanged(self, widget):
		'''Change the selected service'''

		# Get the selected service
		model = self.wTree.get_widget("combo").get_model()
		active = self.wTree.get_widget("combo").get_active()
		if active < 0:
			return
		selectedService = model[active][0]

		self.services = read_services()
		for service in self.services:
			if service['name'] == selectedService:
				self.selected_service = service
				self.refresh()
				return True

	def handle_drop(self, widget, context, x, y, selection, targetType, time ):
		'''Handles the drop of files in the mintUpload window'''
		from urlparse import urlparse
		for tmp in selection.data.splitlines():
			(scheme, netloc, path, params, query, fragment) = urlparse(tmp)
			if not path in self.filenames:
				self.filenames.append(path)
			self.refresh()

	def upload(self, widget):
		'''Start the upload process'''

		uploader = gtkUploader(self.selected_service, self.filenames, self.progressbar, self.statusbar, self.wTree)
		uploader.start()
		return True



class servicesWindow:
	'''The preferences gui'''

	def __init__(self, gladefile, iconfile, mainwin, combo):
		self.iconfile = iconfile
		self.wTree = gtk.glade.XML(gladefile,"services_window")
		self.mainwin = mainwin
		self.gladefile = gladefile

		self.treeview_services = self.wTree.get_widget("treeview_services")
		self.treeview_services_system = self.wTree.get_widget("treeview_services_system")

		self.wTree.get_widget("services_window").set_title(_("Service Preferences"))
		self.wTree.get_widget("services_window").set_icon_from_file(self.iconfile)
		self.wTree.get_widget("services_window").show()

		self.wTree.get_widget("button_close").connect("clicked", self.close_window, self.wTree.get_widget("services_window"), combo)
		self.wTree.get_widget("services_window").connect("destroy", self.close_window, self.wTree.get_widget("services_window"), combo)
		self.wTree.get_widget("toolbutton_add").connect("clicked", self.button_new)
		self.wTree.get_widget("toolbutton_add").set_tooltip_text(_("Create a new service"))
		self.wTree.get_widget("toolbutton_copy").connect("clicked", self.button_copy)
		self.wTree.get_widget("toolbutton_copy").set_tooltip_text(_("Duplicate the selected service"))
		self.wTree.get_widget("toolbutton_edit").connect("clicked", self.button_edit)
		self.wTree.get_widget("toolbutton_edit").set_tooltip_text(_("Edit the service's properties"))
		self.wTree.get_widget("toolbutton_remove").connect("clicked", self.button_remove)
		self.wTree.get_widget("toolbutton_remove").set_tooltip_text(_("Permanently remove the selected service"))

		renderer = gtk.CellRendererText()
		renderer.connect("edited", self.move)
		renderer.set_property("editable", True)

		column1 = gtk.TreeViewColumn(_("Services"), renderer, text=0)
		column1.set_sort_column_id(0)
		column1.set_resizable(True)
		self.treeview_services.append_column(column1)
		self.treeview_services.show()
		column1 = gtk.TreeViewColumn(_("System-wide services"), gtk.CellRendererText(), text=0)
		self.treeview_services_system.append_column(column1)
		self.treeview_services_system.show()
		self.reload_services()

	def close_window(self, widget, window, combo=None):
		window.hide()
		if combo == None:
			self.reload_services()
		else:
			self.mainwin.reload_services(combo)

	def reload_services(self):
		usermodel = gtk.TreeStore(str)
		usermodel.set_sort_column_id( 0, gtk.SORT_ASCENDING )
		sysmodel = gtk.TreeStore(str)
		sysmodel.set_sort_column_id( 0, gtk.SORT_ASCENDING )
		models = {
			'user':usermodel,
			'system':sysmodel
		}
		self.treeview_services.set_model(models['user'])
		self.treeview_services_system.set_model(models['system'])

		self.services = read_services()
		for service in self.services:
			iter = models[service['loc']].insert_before(None, None)
			models[service['loc']].set_value(iter, 0, service['name'])

		del usermodel
		del sysmodel

	def move(self, renderer, path, new_text):
		old_text = renderer.get_property('text')
		for s in self.services:
			if s['name'] == old_text:
				s.move(config_paths['user'] + new_text)
				self.reload_services()
				return

	def button_new(self, widget):
		service = Service('/usr/lib/linuxmint/mintUpload/sample.service')
		sname = "New Service"
		if os.path.exists(config_paths['user'] + sname):
			sname += " 2"
			while os.path.exists(config_paths['user'] + sname):
				next = int(sname[-1:]) + 1
				sname = sname[:-1] + str(next)
		service.filename = config_paths['user'] + sname
		service.write()
		self.services.append(service)

		model = self.treeview_services.get_model()
		iter = model.insert_before(None, None)
		model.set_value(iter, 0, sname)
		self.edit_window(self.treeview_services, model.get_path(iter))

	def button_copy(self, widget):
		selection = self.treeview_services.get_selection()
		(model, iter) = selection.get_selected()
		sname = model.get_value(iter, 0)
		for s in self.services:
			if s['name'] == sname:
				sname += " 2"
				while os.path.exists(config_paths['user'] + sname):
					next = int(sname[-1:]) + 1
					sname = sname[:-1] + str(next)
				s.copy(config_paths['user'] + sname)
				self.reload_services()

	def button_edit(self, widget):
		selection = self.treeview_services.get_selection()
		(model, iter) = selection.get_selected()
		self.edit_window(self.treeview_services, model.get_path(iter))

	def button_remove(self, widget):
		(model, iter) = self.treeview_services.get_selection().get_selected()
		if (iter != None):
			service = model.get_value(iter, 0)
			for s in self.services:
				if s['name'] == service:
					s.remove()
					self.services.remove(s)
			model.remove(iter)

	def edit_window(self, widget, path):
		model = widget.get_model()
		iter = model.get_iter(path)
		sname = model.get_value(iter, 0)
		file = config_paths['user'] + sname

		wTree = gtk.glade.XML(self.gladefile, "dialog_edit_service")
		wTree.get_widget("dialog_edit_service").set_title(_("%s Properties") % sname)
		wTree.get_widget("dialog_edit_service").set_icon_from_file(self.iconfile)
		wTree.get_widget("dialog_edit_service").show()
		wTree.get_widget("button_cancel").connect("clicked", self.close_window, wTree.get_widget("dialog_edit_service"))

		#i18n
		wTree.get_widget("lbl_type").set_label(_("Type:"))
		wTree.get_widget("lbl_hostname").set_label(_("Hostname:"))
		wTree.get_widget("lbl_port").set_label(_("Port:"))
		wTree.get_widget("lbl_username").set_label(_("Username:"))
		wTree.get_widget("lbl_password").set_label(_("Password:"))
		wTree.get_widget("lbl_timestamp").set_label(_("Timestamp:"))
		wTree.get_widget("lbl_path").set_label(_("Path:"))

		wTree.get_widget("lbl_hostname").set_tooltip_text(_("Hostname or IP address, default: ") + defaults['host'])
		wTree.get_widget("txt_host").set_tooltip_text(_("Hostname or IP address, default: ") + defaults['host'])
		wTree.get_widget("txt_host").connect("focus-out-event", self.change, file)

		wTree.get_widget("lbl_port").set_tooltip_text(_("Remote port, default is 21 for FTP, 22 for SFTP and SCP"))
		wTree.get_widget("txt_port").set_tooltip_text(_("Remote port, default is 21 for FTP, 22 for SFTP and SCP"))
		wTree.get_widget("txt_port").connect("focus-out-event", self.change, file)

		wTree.get_widget("lbl_username").set_tooltip_text(_("Username, defaults to your local username"))
		wTree.get_widget("txt_user").set_tooltip_text(_("Username, defaults to your local username"))
		wTree.get_widget("txt_user").connect("focus-out-event", self.change, file)

		wTree.get_widget("lbl_password").set_tooltip_text(_("Password, by default: password-less SCP connection, null-string FTP connection, ~/.ssh keys used for SFTP connections"))
		wTree.get_widget("txt_pass").set_tooltip_text(_("Password, by default: password-less SCP connection, null-string FTP connection, ~/.ssh keys used for SFTP connections"))
		wTree.get_widget("txt_pass").connect("focus-out-event", self.change, file)

		wTree.get_widget("lbl_timestamp").set_tooltip_text(_("Timestamp format (strftime). By default:") + defaults['format'])
		wTree.get_widget("txt_format").set_tooltip_text(_("Timestamp format (strftime). By default:") + defaults['format'])
		wTree.get_widget("txt_format").connect("focus-out-event", self.change, file)

		wTree.get_widget("lbl_path").set_tooltip_text(_("Directory to upload to. <TIMESTAMP> is replaced with the current timestamp, following the timestamp format given. By default: ."))
		wTree.get_widget("txt_path").set_tooltip_text(_("Directory to upload to. <TIMESTAMP> is replaced with the current timestamp, following the timestamp format given. By default: ."))
		wTree.get_widget("txt_path").connect("focus-out-event", self.change, file)

		try:
			config = Service(file)
			try:
				model = wTree.get_widget("combo_type").get_model()
				iter = model.get_iter_first()
				while (iter != None and model.get_value(iter, 0) != config['type'].lower()):
					iter = model.iter_next(iter)
				wTree.get_widget("combo_type").set_active_iter(iter)
				wTree.get_widget("combo_type").connect("changed", self.change, None, file)
			except:
				pass
			try:
				wTree.get_widget("txt_host").set_text(config['host'])
			except:
				wTree.get_widget("txt_host").set_text("")
			try:
				wTree.get_widget("txt_port").set_text(str(config['port']))
			except:
				wTree.get_widget("txt_port").set_text("")
			try:
				wTree.get_widget("txt_user").set_text(config['user'])
			except:
				wTree.get_widget("txt_user").set_text("")
			try:
				wTree.get_widget("txt_pass").set_text(config['pass'])
			except:
				wTree.get_widget("txt_pass").set_text("")
			try:
				wTree.get_widget("txt_format").set_text(config['format'])
			except:
				wTree.get_widget("txt_format").set_text("")
			try:
				wTree.get_widget("txt_path").set_text(config['path'])
			except:
				wTree.get_widget("txt_path").set_text("")
		except Exception, detail:
			print detail
	
	def change(self, widget, event, file):
		try:
			wname = widget.get_name()
			if wname == "combo_type":
				model = widget.get_model()
				iter = 	widget.get_active_iter()
				config = { 'type' : model.get_value(iter, 0) }
			else:
				config = { wname[4:] : widget.get_text() }
			s = Service(file)
			s.merge(config)
			s.write()
		except Exception as e:
			try:    raise CustomError(_("Could not save configuration change"), e)
			except: pass



if __name__ == "__main__":
	if len(sys.argv) >=2 and sys.argv[1] == "--version":
		print "mintupload: %s" % __version__
		exit(0)
	if len(sys.argv) >=2 and sys.argv[1] in ["-h","--help"]:
		print """Usage: mintupload.py path/to/filename"""
		exit(0)

	filenames = sys.argv[1:]
	mainwin = mintUploadWindow(filenames)
	gtk.main()
