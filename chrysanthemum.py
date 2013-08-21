#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Chrysanthemum Python Code Inspector

Create by monkeycz <monkeycz@hotmail.com>
2011/01/20 19:38:58
'''

import sys, os, marshal, dis, opcode, StringIO
from PyQt4 import QtGui, QtCore, Qt, QtWebKit
import hexedit
import chrysanthemum_rc

CO_OPTIMIZED, CO_NEWLOCALS, CO_VARARGS, CO_VARKEYWORDS = 0x1, 0x2, 0x4, 0x8
CO_NESTED, CO_GENERATOR, CO_NOFREE = 0x10, 0x20, 0x40

class HexViewCodeObjectSource(hexedit.HexViewDataSource):

	def __init__(self, code_object):
		super(HexViewCodeObjectSource, self).__init__()
		self.code_object = code_object

	def read(self, size, pos):
		return self.code_object.co_code[pos:pos+size]

	def write(self, data, pos):
		pass

	def length(self):
		return len(self.code_object.co_code)

def load_code_object(filename):
	try:
		ext = os.path.splitext(filename)[1]
		if ext == '.py' or ext == '.pyw':
			return compile(open(filename).read(), filename, 'exec')
		elif ext == '.pyc' or ext == '.pyo':
			f = open(filename, 'rb')
			f.seek(8)
			return marshal.load(f)
		else:
			raise
	except:
		return None

def walk_code_object(code_object):
	return [code_object, [walk_code_object(const) for const in code_object.co_consts if hasattr(const, 'co_code')]]

def html_format(text):
	escape_list = (('&', '&amp;'), ('\x09', '&nbsp;&nbsp;&nbsp;&nbsp;'), ('\x20', '&nbsp;'), ('<', '&lt;'), ('>', '&gt;'), ('"', '&quot;'), ('\'', '&apos;'), ('\n', '<br>'))
	for old, new in escape_list:
		text = text.replace(old, new)
	return text

def generate_disassembly(co, lasti=-1):
	report_template = '''
	<!DOCTYPE HTML>
	<html>
	<head>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
	<title>Disassembly</title>
	<style type="text/css">
	body {
		font-family: "Courier New", Monospace, Monaco, Fixedsys, Courier;
		color: #ffffff;
		background-color: #001b33;
	}
	ul {
		list-style-type: none;
	}
	li.src_line {
	}
	li.src_line:hover {
		background-color: #003b70;
	}
	li[class^="op_line"] {
	}
	li[class^="op_line"]:hover {
		background-color: #003b70;
	}
	li.op_line_start {
		list-style-type: square;
	}
	li.op_line_jump {
		list-style-type: disc;
	}
	span {
		display: inline-block;
	}
	span.tab {
		display: none;
	}
	span.line_no {
		width: 40px;
		margin-left: 5px;
		margin-right: 5px;
		text-align: right;
		color: #0065bf;
	}
	span.src {
		width: 500px;
		color: #0088ff;
	}
	span.filename {
		width: 500px;
		color: #0088ff;
	}
	span.address {
		width: 40px;
		margin-left: 20px;
		margin-right: 5px;
		text-align: right;
		color: #0065bf;
	}
	span.op {
		width: 70px;
		margin-left: 5px;
		margin-right: 15px;
		color: #000d1a;
	}
	span.opname {
		width: 150px;
		margin-left: 5px;
		margin-right: 5px;
	}
	span.oparg {
		width: 50px;
		margin-left: 5px;
		margin-right: 5px;
		text-align: right;
		color: #ff0044;
	}
	span.decoration {
		width: 300px;
		margin-left: 5px;
		margin-right: 5px;
		color: #ff9d00;
	}
	span.decoration a {
		color: #3ad900;
		text-decoration: none;
	}
	span.decoration a:link {
	}
	span.decoration a:hover {
		text-decoration:underline;
	}
	span.decoration a:active {
		text-decoration:underline;
	}
	span.decoration a:visited {
	}
	</style>
	</head>
	<body>
	<div id="disassembly">
	%s
	</div>
	</body>
	</html>
	'''

	report = StringIO.StringIO()

	try:
		src_lines = open(co.co_filename).readlines()
	except:
		src_lines = []

	code = co.co_code
	labels = dis.findlabels(code)
	linestarts = dict(dis.findlinestarts(co))
	n = len(code)
	i = 0
	extended_arg = 0
	free = None
	into_op_block = False

	while i < n:
		if not into_op_block:
			report.write('<ul>')

		if i in linestarts:
			report.write('<li class="src_line">')
			line_no = linestarts[i]
			try:
				report.write('<span class="line_no">%d</span><span class="tab">&nbsp;</span><span class="src">%s</span>' % 
					(line_no, html_format(src_lines[line_no - 1].rstrip())))
			except:
				report.write('<span class="line_no">%d</span><span class="tab">&nbsp;</span><span class="filename">(\'%s\')</span>' % 
					(line_no, html_format(co.co_filename)))
			report.write('</li>')

		if not into_op_block:
			report.write('<ul>')
			into_op_block = True

		report.write('<li class="op_line_%s"><a name="%d"></a>' % 
			('start' if i == lasti else 'jump' if i in labels else 'normal', i))

		op = ord(code[i])
		i = i + 1

		opname = opcode.opname[op]

		if op >= opcode.HAVE_ARGUMENT:
			oparg_low = ord(code[i])
			oparg_high = ord(code[i + 1])
			i = i + 2

			oparg = oparg_low + oparg_high * 256 + extended_arg
			extended_arg = 0

			if op == opcode.EXTENDED_ARG:
				extended_arg = oparg * 65536L

			if op in opcode.hasconst:
				const = co.co_consts[oparg]
				if hasattr(const, 'co_code'):
					decoration = '<a href="{0}">({0})</a>'.format(const.co_name)
				else:
					decoration = html_format('({0}: {1})'.format(repr(const), type(const)))
			elif op in opcode.hasname:
				decoration = html_format('({0})'.format(repr(co.co_names[oparg])))
			elif op in opcode.hasjrel:
				decoration = '<a href="#{0}">(=> {0})</a>'.format(i + oparg)
			elif op in opcode.hasjabs:
				decoration = '<a href="#{0}">(=> {0})</a>'.format(oparg)
			elif op in opcode.haslocal:
				decoration = html_format('({0})'.format(repr(co.co_varnames[oparg])))
			elif op in opcode.hascompare:
				decoration = html_format('({0})'.format(opcode.cmp_op[oparg]))
			elif op in opcode.hasfree:
				if free is None:
					free = co.co_cellvars + co.co_freevars
				decoration = html_format('({0})'.format(repr(free[oparg])))
			elif opname == 'CALL_FUNCTION':
				decoration = html_format('(pos args: {0}, key args: {1})'.format(oparg_low, oparg_high))
			elif opname == 'MAKE_FUNCTION':
				decoration = html_format('(default args: {0})'.format(oparg))
			else:
				decoration = ''

			report.write('<span class="address">%d</span><span class="tab">&nbsp;</span><span class="op">%02x&nbsp;%02x%02x</span><span class="tab">&nbsp;</span><span class="opname">%s</span><span class="tab">&nbsp;</span><span class="oparg">%d</span><span class="tab">&nbsp;</span><span class="decoration">%s</span>' % 
				(i - 3, op, oparg_low, oparg_high, html_format(opname), oparg, decoration))
		else:
			report.write('<span class="address">%d</span><span class="tab">&nbsp;</span><span class="op">%02x</span><span class="tab">&nbsp;</span><span class="opname">%s</span>' % 
				(i - 1, op, html_format(opname)))

		report.write('</li>')

		if i in linestarts or i >= n:
			report.write('</ul></ul>')
			into_op_block = False

	return report_template % report.getvalue()

def generate_summary(code_object):
	report_template = '''
	<!DOCTYPE HTML>
	<html>
	<head>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
	<title>Summary</title>
	<style type="text/css">
	body {
		font-family: "Courier New", Monospace, Monaco, Fixedsys, Courier;
		color: #ffffff;
		background-color: #001b33;
	}
	hr {
		color: #ffffff;
		size: 5;
		align: center;
	}
	li {
	}
	li:hover {
		background-color: #003b70;
	}
	li.key {
		color: #ff9d00;
	}
	li.value {
	}
	li.value a {
		color: #3ad900;
		text-decoration: none;
	}
	li.value a:link {
	}
	li.value a:hover {
		text-decoration:underline;
	}
	li.value a:active {
		text-decoration:underline;
	}
	li.value a:visited {
	}
	</style>
	</head>
	<body>
	<div id="summary">
	%s
	</div>
	</body>
	</html>
	'''

	report = StringIO.StringIO()

	varargs = bool(code_object.co_flags & CO_VARARGS)
	varkwargs = bool(code_object.co_flags & CO_VARKEYWORDS)
	newlocals = bool(code_object.co_flags & CO_NEWLOCALS)

	def generate_list_content(key):
		report.write('<ul>')
		report.write('<li class="key">%s</li>' % html_format(key))
		report.write('<ul>')
		item = getattr(code_object, key)
		if not hasattr(item, '__iter__'):
			item = [item]
		for index, value in enumerate(item):
			report.write('<li class="value">%s</li>' % generate_decoration(key, value, index))
		report.write('</ul></ul>')

	def generate_decoration(key, value, index):
		if key == 'co_flags':
			flag_list = dict(CO_OPTIMIZED=CO_OPTIMIZED, CO_NEWLOCALS=CO_NEWLOCALS, CO_VARARGS=CO_VARARGS, 
				CO_VARKEYWORDS=CO_VARKEYWORDS, CO_NESTED=CO_NESTED, CO_GENERATOR=CO_GENERATOR, 
				CO_NOFREE=CO_NOFREE)
			flag_name_list = []
			for flag_name, flag_value in flag_list.iteritems():
				if value & flag_value:
					flag_name_list.append(flag_name)
			return html_format('{0}: {1}'.format(value, ', '.join(flag_name_list)))
		elif key == 'co_consts':
			if hasattr(value, 'co_code'):
				return '<a href="{0}">{0}</a>'.format(value.co_name)
			else:
				return html_format('{0}: {1}'.format(repr(value), type(value)))
		elif key == 'co_varnames':
			if index < code_object.co_argcount:
				return html_format('{0} (pos arg: {1})'.format(repr(value), index))
			elif varargs and index == code_object.co_argcount + varargs - 1:
				return html_format('{0} (excess pos arg (*args))'.format(repr(value)))
			elif varkwargs and index == code_object.co_argcount + varargs + varkwargs - 1:
				return html_format('{0} (excess key arg (**kwargs))'.format(repr(value)))
		return html_format(repr(value))

	def draw_line():
		report.write('<hr>')

	generate_list_content('co_name')
	generate_list_content('co_filename')

	draw_line()

	generate_list_content('co_argcount')
	generate_list_content('co_nlocals')
	generate_list_content('co_stacksize')
	generate_list_content('co_flags')

	draw_line()

	generate_list_content('co_consts')
	generate_list_content('co_names')
	generate_list_content('co_varnames')
	generate_list_content('co_freevars')
	generate_list_content('co_cellvars')

	return report_template % report.getvalue()

def generate_welcome():
	report_template = '''
	<!DOCTYPE HTML>
	<html>
	<head>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
	<title>Welcome</title>
	<style type="text/css">
	body {
		font-family: "Courier New", Monospace, Monaco, Fixedsys, Courier;
		color: #000000;
		background-color: #ffffff;
	}
	div#welcome {
		text-align: center;
	}
	</style>
	</head>
	<body>
	<div id="welcome">
	%s
	</div>
	</body>
	</html>
	'''

	report = StringIO.StringIO()

	report.write('<p>%s</p>' % html_format(__doc__))
	report.write('<a href="#" onclick="chrysanthemum.open();">')
	report.write('<img id="logo" src="qrc:/images/logo.png">')
	report.write('</a>')
	report.write('<p>%s</p>' % html_format('Chrysanthemum protection is everyone\'s responsibility'))

	return report_template % report.getvalue()

def fill_model(code_object_tree, model):
	if code_object_tree:
		code_object = code_object_tree[0]
		if code_object.co_name == '<module>' and code_object.co_filename:
			title = os.path.basename(code_object.co_filename)
		else:
			title = code_object.co_name
		item = QtGui.QStandardItem()
		item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
		item.setData(title, QtCore.Qt.DisplayRole)
		item.setData(code_object, QtCore.Qt.UserRole + 1)
		model.appendRow(item)
		map(lambda x:fill_model(x, item), code_object_tree[1])

def map_model_index_to_path(index):
	def walk_model_index(index):
		while index.isValid():
			yield str(index.data(QtCore.Qt.DisplayRole).toString())
			index = index.parent()
		return
	return '/'.join(reversed(list(walk_model_index(index))))

def map_path_to_model_index(path, model):
	def walk_path_list(path_iter, item):
		try:
			path_item = path_iter.next()
		except StopIteration:
			return None
		for r in xrange(0, item.rowCount()):
			if type(item) == QtGui.QStandardItemModel:
				child_item = item.item(r)
			elif type(item) == QtGui.QStandardItem:
				child_item = item.child(r)
			else:
				continue
			if path_item == child_item.data(QtCore.Qt.DisplayRole).toString():
				result_item = walk_path_list(path_iter, child_item)
				return result_item if result_item else child_item
		return None
	result_item = walk_path_list(iter(path.split('/')), model)
	return result_item.index() if result_item else None

class MainWindow(QtGui.QMainWindow):

	def __init__(self, parent=None, flags=QtCore.Qt.Widget):
		super(MainWindow, self).__init__(parent, flags)

		splitter_widget = QtGui.QSplitter(QtCore.Qt.Horizontal)

		self.code_object_view = QtGui.QTreeView(splitter_widget)
		self.code_object_view.setHeaderHidden(True)
		self.code_object_view.setModel(QtGui.QStandardItemModel())
		self.code_object_view.selectionModel().currentChanged.connect(self.on_code_object_view_current_changed)

		tab_widget = QtGui.QTabWidget(splitter_widget)

		self.summary_view = QtWebKit.QWebView()
		self.summary_view.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
		self.summary_view.linkClicked.connect(self.on_summary_view_link_clicked)

		self.disassembly_view = QtWebKit.QWebView()
		self.disassembly_view.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
		self.disassembly_view.linkClicked.connect(self.on_disassembly_view_link_clicked)

		self.hex_edit = hexedit.HexEdit()

		tab_widget.addTab(self.summary_view, 'Summary')
		tab_widget.addTab(self.disassembly_view, 'Disassembly')
		tab_widget.addTab(self.hex_edit, 'Hex Dump')

		menu = self.menuBar().addMenu('&File')
		menu.addAction('&Open...').triggered.connect(self.on_menu_bar_open_triggered)
		menu.addAction('&Close').triggered.connect(self.on_menu_bar_close_triggered)
		menu.addAction('&Reload').triggered.connect(self.on_menu_bar_reload_triggered)
		menu.addSeparator()
		menu.addAction('E&xit').triggered.connect(Qt.qApp.quit)
		menu = self.menuBar().addMenu('&Help')
		menu.addAction('About...').triggered.connect(self.on_menu_bar_about_triggered)
		menu.addSeparator()
		menu.addAction('About Qt...').triggered.connect(Qt.qApp.aboutQt)

		splitter_widget.setStretchFactor(0, 0)
		splitter_widget.setStretchFactor(1, 1)
		splitter_widget.setSizes([200, splitter_widget.width()-200])

		self.setCentralWidget(splitter_widget)
		self.setWindowTitle('Chrysanthemum')
		self.setWindowIcon(QtGui.QIcon(':/images/icon.png'))
		self.setAcceptDrops(True)
		self.resize(1024, 768)
		
		self.setGeometry(QtGui.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter, self.size(), QtGui.QDesktopWidget().availableGeometry()))

		self.close()

	def open_file_list(self, file_list):
		map(lambda x:fill_model(walk_code_object(load_code_object(x)), self.code_object_view.model()), file_list)

	def handle_code_object(self, code_object, code_object_path):
		self.summary_view.setHtml(generate_summary(code_object), 
			QtCore.QUrl('pycode://summary/%s/' % code_object_path))
		self.disassembly_view.setHtml(generate_disassembly(code_object), 
			QtCore.QUrl('pycode://disassembly/%s/' % code_object_path))
		self.hex_edit.set_data_source(HexViewCodeObjectSource(code_object))
		self.statusBar().showMessage(code_object.co_filename)

	def handle_pycode_url(self, url):
		if url.scheme() != 'pycode':
			return
		host = url.host()
		view = getattr(self, '%s_view' % host)
		if url.path() == view.url().path():
			view.setHtml(view.page().mainFrame().toHtml(), url)
		else:
			index = map_path_to_model_index(url.path()[1:], self.code_object_view.model())
			if index:
				self.code_object_view.selectionModel().setCurrentIndex(index, QtGui.QItemSelectionModel.ToggleCurrent)

	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls():
			event.accept()

	def dropEvent(self, event):
		file_list = [str(url.toLocalFile()) for url in event.mimeData().urls()]
		self.all_file_list += file_list
		self.open_file_list(file_list)

	@QtCore.pyqtSlot()
	def open(self):
		file_list = map(str, QtGui.QFileDialog.getOpenFileNames(self, filter='Python files (*.py *.pyw *.pyc *.pyo);;All files (*.*)'))
		self.all_file_list += file_list
		self.open_file_list(file_list)

	@QtCore.pyqtSlot()
	def close(self):
		self.all_file_list = []
		self.code_object_view.model().clear()
		self.summary_view.setHtml(generate_welcome(), QtCore.QUrl('pycode://summary/'))
		self.summary_view.page().mainFrame().addToJavaScriptWindowObject('chrysanthemum', self)
		self.disassembly_view.setHtml('', QtCore.QUrl('pycode://disassembly/'))
		self.hex_edit.set_data_source(hexedit.HexViewDataSource())
		self.statusBar().showMessage('')

	@QtCore.pyqtSlot()
	def reload(self):
		file_list = self.all_file_list
		self.close()
		self.all_file_list = file_list
		self.open_file_list(file_list)

	@QtCore.pyqtSlot()
	def about(self):
		QtGui.QMessageBox.about(self, self.windowTitle(), __doc__)

	@QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
	def on_code_object_view_current_changed(self, current, previous):
		code_object = current.data(QtCore.Qt.UserRole + 1).toPyObject()
		code_object_path = map_model_index_to_path(current)
		self.handle_code_object(code_object, code_object_path)

	@QtCore.pyqtSlot(QtCore.QUrl)
	def on_summary_view_link_clicked(self, url):
		self.handle_pycode_url(url)

	@QtCore.pyqtSlot(QtCore.QUrl)
	def on_disassembly_view_link_clicked(self, url):
		self.handle_pycode_url(url)

	@QtCore.pyqtSlot(bool)
	def on_menu_bar_open_triggered(self, checked=False):
		self.open()

	@QtCore.pyqtSlot(bool)
	def on_menu_bar_close_triggered(self, checked=False):
		self.close()

	@QtCore.pyqtSlot(bool)
	def on_menu_bar_reload_triggered(self, checked=False):
		self.reload()

	@QtCore.pyqtSlot(bool)
	def on_menu_bar_about_triggered(self, checked=False):
		self.about()

def main():
	app = QtGui.QApplication(sys.argv)
	window = MainWindow()
	window.show()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
