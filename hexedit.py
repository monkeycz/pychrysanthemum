# =====================================================
# HexEdit
# -----------------------------------------------------
# create by monkeycz <monkeycz@hotmail.com>
# 2010/11/24 17:14:03
# =====================================================

from PyQt4 import QtGui, QtCore, Qt
import sys, os, string, platform

class HexViewDataSource(object):

	def __init__(self):
		pass

	def read(self, size, pos):
		return ''

	def write(self, data, pos):
		pass

	def length(self):
		return 0

class HexViewFileSource(HexViewDataSource):

	def __init__(self, filename):
		super(HexViewFileSource, self).__init__()
		self.f = open(filename, 'rb+')

	def read(self, size, pos):
		self.f.seek(pos)
		return self.f.read(size)

	def write(self, data, pos):
		self.f.seek(pos)
		self.f.write(data)

	def length(self):
		pos = self.f.tell()
		self.f.seek(0, os.SEEK_END)
		l = self.f.tell()
		self.f.seek(pos, os.SEEK_SET)
		return l

class HexViewMemorySource(HexViewDataSource):
	pass

class HexView(QtGui.QFrame):

	SELECTED_REGION_HIDDEN = 0
	SELECTED_REGION_SLICE = 1
	SELECTED_REGION_BLOCK = 2

	VIEW_HEX = 0
	VIEW_CHAR = 1

	data_source_changed = QtCore.pyqtSignal(int, int)
	data_changed = QtCore.pyqtSignal(int, int)
	data_pos_changed = QtCore.pyqtSignal(int)
	cursor_pos_changed = QtCore.pyqtSignal(int)
	selected_region_changed = QtCore.pyqtSignal(int, int, int)
	address_list_changed = QtCore.pyqtSignal(list)

	def paintEvent(self, event):
		super(HexView, self).paintEvent(event)

		painter = QtGui.QPainter(self)
		painter.setFont(Qt.QFont(self.font_name, self.font_size))

		flag = QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop | QtCore.Qt.TextDontClip | QtCore.Qt.TextSingleLine
		self.line_height = painter.boundingRect(QtCore.QRect(), flag, 'f').height()

		if not self.data:
			is_need_update_address_list = True
			self.byte_num_per_page = self.size().height() // self.line_height * self.byte_num_per_line
			self.data = self.data_source.read(self.byte_num_per_page + self.byte_num_per_line, self.data_pos)
		else:
			is_need_update_address_list = False

		painter.setPen(QtCore.Qt.black)

		self.line_rect_list = []
		data_iter = iter(self.data)
		byte_offset = 0
		line_count = len(self.data) // self.byte_num_per_line
		if len(self.data) % self.byte_num_per_line != 0:
			line_count += 1
		if line_count == 0:
			return

		for line_index in xrange(0, line_count):
			line_x = 0
			line_y = line_index * self.line_height
			byte_x = line_x
			byte_y = line_y

			byte_rect_list = []

			for i, c in enumerate(data_iter):
				if self.view_mode == HexView.VIEW_HEX:
					v = c.encode('hex')
				else:
					v = c if ord(c) in xrange(32, 128 + 1) else '.'

				content_rect = painter.drawText(QtCore.QRect(byte_x, byte_y, 0, 0), flag, v)
				byte_x += content_rect.width()

				range_rect = QtCore.QRect(content_rect)

				if (i + 1 != self.byte_num_per_line) and (self.view_mode == HexView.VIEW_HEX):
					edge_rect = painter.drawText(QtCore.QRect(byte_x, byte_y, 0, 0), flag, ' ')
					range_rect.setWidth(edge_rect.x() - content_rect.x() + edge_rect.width())
					byte_x += edge_rect.width()

				byte_pos = self.data_pos + byte_offset
				byte_rect_list.append((content_rect, range_rect, byte_pos))
				byte_offset += 1

				if i + 1 == self.byte_num_per_line:
					break

			line_rect = QtCore.QRect(line_x, line_y, byte_x - line_x, self.line_height)
			self.line_rect_list.append((byte_rect_list, line_rect))

		if is_need_update_address_list:
			self.address_list = []
			address = self.data_pos
			for byte_rect_list, line_rect in self.line_rect_list:
				self.address_list.append(address)
				address += len(byte_rect_list)
			self.address_list_changed.emit(self.address_list)

		painter.setPen(QtCore.Qt.NoPen)
		painter.setCompositionMode(QtGui.QPainter.RasterOp_SourceAndDestination)

		if self.hasFocus():
			selected_region_brush = Qt.qApp.palette().highlight()
		else:
			selected_region_brush = Qt.qApp.palette().dark()		
		painter.setBrush(selected_region_brush)

		selected_rect_info = self.get_selected_rect_info(self.cursor_pos, self.cursor_pos)
		if selected_rect_info:
			(cursor_rect, _), (_, _)= selected_rect_info
			painter.drawRect(cursor_rect)

		if self.selected_region_mode == HexView.SELECTED_REGION_HIDDEN:
			return

		painter.setBrush(Qt.qApp.palette().toolTipBase())

		selected_rect_info = self.get_selected_rect_info(self.begin_selected_byte_pos, self.end_selected_byte_pos)
		if selected_rect_info:
			(begin_byte_rect, begin_line_index), (end_byte_rect, end_line_index) = selected_rect_info
			if (self.selected_region_mode == HexView.SELECTED_REGION_BLOCK) or (begin_line_index == end_line_index):
				if begin_byte_rect.x() > end_byte_rect.x():
					begin_byte_rect, end_byte_rect = \
						QtCore.QRect(QtCore.QPoint(end_byte_rect.x(), begin_byte_rect.y()), end_byte_rect.size()), \
						QtCore.QRect(QtCore.QPoint(begin_byte_rect.x(), end_byte_rect.y()), begin_byte_rect.size())
				painter.drawRect(QtCore.QRect(begin_byte_rect.topLeft(),
					QtCore.QSize(end_byte_rect.x() - begin_byte_rect.x() + end_byte_rect.width(), \
						end_byte_rect.y() - begin_byte_rect.y() + end_byte_rect.height())))
			else:
				byte_rect_list, begin_line_rect = self.line_rect_list[begin_line_index]
				byte_rect_list, end_line_rect = self.line_rect_list[end_line_index]
				for byte_rect_list, line_rect in self.line_rect_list[(begin_line_index + 1):(end_line_index)]:
					painter.drawRect(line_rect)
				painter.drawRect(QtCore.QRect(begin_byte_rect.topLeft(),
					QtCore.QSize(begin_line_rect.x() + begin_line_rect.width() - begin_byte_rect.x(), begin_line_rect.height())))
				painter.drawRect(QtCore.QRect(end_line_rect.topLeft(),
					QtCore.QSize(end_byte_rect.x() + end_byte_rect.width() - end_line_rect.x(), end_line_rect.height())))

	def get_selected_rect_info(self, begin_selected_byte_pos, end_selected_byte_pos):
		is_find_begin = False
		is_find_end = False
		is_end = False
		for line_index, (byte_rect_list, line_rect) in enumerate(self.line_rect_list):
			for content_rect, range_rect, byte_pos in byte_rect_list:
				if not is_find_begin:
					if byte_pos >= begin_selected_byte_pos:
						begin_byte_rect = content_rect
						begin_line_index = line_index
						is_find_begin = True
				if is_find_begin and not is_end:
					if byte_pos <= end_selected_byte_pos:
						end_byte_rect = content_rect
						end_line_index = line_index
						is_find_end = True
					else:
						is_end = True
				if is_find_begin and is_find_end and is_end:
					break
			else:
				continue
			break

		if not is_find_begin or not is_find_end:
			return ()
		else:
			return ((begin_byte_rect, begin_line_index), (end_byte_rect, end_line_index))

	def get_selected_byte_pos(self, selected_pos):
		if not self.line_rect_list:
			return 0

		first_line_index = 0
		last_line_index = len(self.line_rect_list) - 1
		if selected_pos.y() <= self.line_rect_list[first_line_index][1].y():
			selected_line_index = first_line_index
		elif selected_pos.y() >= self.line_rect_list[last_line_index][1].y():
			selected_line_index = last_line_index
		else:
			selected_line_index = selected_pos.y() // self.line_height

		byte_rect_list = self.line_rect_list[selected_line_index][0]
		first_byte_index = 0
		last_byte_index = len(byte_rect_list) - 1
		if selected_pos.x() <= byte_rect_list[first_byte_index][1].x():
			selected_byte_pos = byte_rect_list[first_byte_index][2]
		elif selected_pos.x() >= byte_rect_list[last_byte_index][1].x():
			selected_byte_pos = byte_rect_list[last_byte_index][2]
		else:
			for byte_rect in reversed(byte_rect_list):
				if selected_pos.x() >= byte_rect[1].x():
					selected_byte_pos = byte_rect[2]
					break
			else:
				selected_byte_pos = byte_rect_list[last_byte_index][2]

		return selected_byte_pos

	def selecting_begin_selected_region(self, pos):
		self.selecting_begin_selected_byte_pos = self.get_selected_byte_pos(pos)

	def selecting_end_selected_region(self, pos):
		self.selecting_end_selected_byte_pos = self.get_selected_byte_pos(pos)
		current_begin_selected_byte_pos = min(self.selecting_begin_selected_byte_pos, self.selecting_end_selected_byte_pos)
		current_end_selected_byte_pos = max(self.selecting_begin_selected_byte_pos, self.selecting_end_selected_byte_pos)
		if (self.begin_selected_byte_pos != current_begin_selected_byte_pos) or \
			(self.end_selected_byte_pos != current_end_selected_byte_pos) or \
			(current_begin_selected_byte_pos == current_end_selected_byte_pos):
			self.update_selected_region_pos(current_begin_selected_byte_pos, current_end_selected_byte_pos)
			self.update_cursor_pos(self.selecting_end_selected_byte_pos)		

	def mousePressEvent(self, event):
		if Qt.qApp.keyboardModifiers() == QtCore.Qt.AltModifier:
			self.selected_region_mode = HexView.SELECTED_REGION_BLOCK
		else:
			self.selected_region_mode = HexView.SELECTED_REGION_SLICE

		self.selecting_begin_selected_region(event.pos())
		self.selecting_end_selected_region(event.pos())

	def mouseMoveEvent(self, event):
		if event.pos().y() < 0:
			self.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Up, QtCore.Qt.NoModifier))
		elif event.pos().y() > self.size().height():
			self.keyPressEvent(QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Down, QtCore.Qt.NoModifier))

		self.selecting_end_selected_region(event.pos())

	def mouseReleaseEvent(self, event):
		pass

	def keyPressEvent(self, event):
		modifier = event.modifiers()
		key = event.key()
		text = event.text()
		if key == QtCore.Qt.Key_Escape:
			self.hide_selected_region()
		elif key == QtCore.Qt.Key_Up:
			if self.cursor_pos - self.data_pos < self.byte_num_per_line:
				self.update_data_and_cursor(self.data_pos - self.byte_num_per_line)
			else:
				self.update_cursor_pos(self.cursor_pos - self.byte_num_per_line)
		elif key == QtCore.Qt.Key_Down:
			if self.cursor_pos - self.data_pos >= self.byte_num_per_page - self.byte_num_per_line:
				self.update_data_and_cursor(self.data_pos + self.byte_num_per_line)
			else:
				self.update_cursor_pos(self.cursor_pos + self.byte_num_per_line)
		elif key == QtCore.Qt.Key_Left:
			if self.cursor_pos - self.data_pos < 1:
				self.update_data_pos(self.data_pos - self.byte_num_per_line)
			self.update_cursor_pos(self.cursor_pos - 1)
		elif key == QtCore.Qt.Key_Right:
			if self.cursor_pos - self.data_pos >= self.byte_num_per_page - 1:
				self.update_data_pos(self.data_pos + self.byte_num_per_line)
			self.update_cursor_pos(self.cursor_pos + 1)
		elif key == QtCore.Qt.Key_PageUp:
			self.update_data_and_cursor(self.data_pos - self.byte_num_per_page)
		elif key == QtCore.Qt.Key_PageDown:
			self.update_data_and_cursor(self.data_pos + self.byte_num_per_page)
		elif (modifier == QtCore.Qt.ControlModifier) and (key == QtCore.Qt.Key_C):
			self.copy_selected_data()
		elif text:
			self.edit_selected_data(text)

	def wheelEvent(self, event):
		degree_num = event.delta() // 8
		step_num = degree_num // 15
		orientation = event.orientation()
		if orientation == QtCore.Qt.Horizontal:
			self.update_data_pos(self.data_pos - 1 * step_num)
		elif orientation == QtCore.Qt.Vertical:
			self.update_data_and_cursor(self.data_pos - self.byte_num_per_line * step_num)

	def resizeEvent(self, event):
		self.update_view()

	def update_view(self):
		self.data = None
		self.update()

	def hide_selected_region(self):
		self.update_selected_region_mode(HexView.SELECTED_REGION_HIDDEN)

	def edit_selected_data(self, text):
		text = '%s' % text
		if len(text) != 1:
			return
		if self.view_mode == HexView.VIEW_HEX:
			if text not in string.hexdigits:
				return
			cursor_data = self.data_source.read(1, self.cursor_pos)
			if not self.is_editing_half_byte:
				edited_data = chr(int(text, 16) << 4 | (ord(cursor_data) & 0x0f))
				cursor_move_offset = 0
			else:
				edited_data = chr(int(text, 16) << 0 | (ord(cursor_data) & 0xf0))
				cursor_move_offset = 1
			self.is_editing_half_byte = not self.is_editing_half_byte
		else:
			edited_data = text
			cursor_move_offset = 1
		self.data_source.write(edited_data, self.cursor_pos)
		if cursor_move_offset != 0:
			self.update_cursor_pos(self.cursor_pos + cursor_move_offset)
		self.update_data_pos(self.data_pos)

	def copy_selected_data(self):
		if self.selected_region_mode == HexView.SELECTED_REGION_HIDDEN:
			return
		selected_data = self.data_source.read(self.end_selected_byte_pos - self.begin_selected_byte_pos + 1, self.begin_selected_byte_pos)
		if self.view_mode == HexView.VIEW_HEX:
			selected_text = ''.join('%02x' % ord(v) for v in selected_data)
		else:
			selected_text = selected_data
		try:
			import win32clipboard
			import win32con
			win32clipboard.OpenClipboard()
			win32clipboard.EmptyClipboard()
			win32clipboard.SetClipboardData(win32con.CF_TEXT, selected_text)
			win32clipboard.CloseClipboard()
		except:
			pass

	def update_data_and_cursor(self, pos):
		self.update_cursor_pos(self.cursor_pos - self.data_pos + pos)
		self.update_data_pos(pos)

	@QtCore.pyqtSlot(int)
	def update_data_and_cursor_no_signal(self, pos):
		self.update_cursor_pos_no_signal(self.cursor_pos - self.data_pos + pos)
		self.update_data_pos_no_signal(pos)

	def update_data_pos(self, pos):
		self.update_data_pos_no_signal(pos)
		self.data_pos_changed.emit(pos)

	@QtCore.pyqtSlot(int)
	def update_data_pos_no_signal(self, pos):
		self.data_pos = pos
		self.update_view()

	def update_cursor_pos(self, pos):
		self.update_cursor_pos_no_signal(pos)
		self.cursor_pos_changed.emit(pos)

	@QtCore.pyqtSlot(int)
	def update_cursor_pos_no_signal(self, pos):
		self.cursor_pos = pos
		self.update()

	def update_selected_region_pos(self, begin_selected_byte_pos, end_selected_byte_pos):
		selected_region_mode = self.selected_region_mode
		self.update_selected_region(selected_region_mode, begin_selected_byte_pos, end_selected_byte_pos)

	def update_selected_region_mode(self, selected_region_mode):
		begin_selected_byte_pos = self.begin_selected_byte_pos
		end_selected_byte_pos = self.end_selected_byte_pos
		self.update_selected_region(selected_region_mode, begin_selected_byte_pos, end_selected_byte_pos)

	def update_selected_region(self, selected_region_mode, begin_selected_byte_pos, end_selected_byte_pos):
		self.update_selected_region_no_signal(selected_region_mode, begin_selected_byte_pos, end_selected_byte_pos)
		self.selected_region_changed.emit(selected_region_mode, begin_selected_byte_pos, end_selected_byte_pos)

	@QtCore.pyqtSlot(int, int, int)
	def update_selected_region_no_signal(self, selected_region_mode, begin_selected_byte_pos, end_selected_byte_pos):
		self.selected_region_mode = selected_region_mode
		self.begin_selected_byte_pos = begin_selected_byte_pos
		self.end_selected_byte_pos = end_selected_byte_pos
		self.update()

	def __setattr__(self, name, value):
		if name == 'data_source':
			if not value:
				self.data_source_changed.emit(0, 0)
			else:
				self.data_source_changed.emit(0, value.length())
		elif name == 'data':
			if not value:
				self.data_changed.emit(0, 0)
			else:
				self.data_changed.emit(self.byte_num_per_line, self.byte_num_per_page)
		elif (name == 'data_pos') or (name == 'cursor_pos') or \
			 (name == 'begin_selected_byte_pos') or (name == 'end_selected_byte_pos'):
			if (not self.data_source) or (value < 0):
				value = 0
			else:
				data_source_length = self.data_source.length()
				if data_source_length == 0:
					value = 0
				elif value >= data_source_length:
					value = data_source_length - 1
		elif name == 'selected_region_mode':
			self.is_editing_half_byte = False

		super(HexView, self).__setattr__(name, value)

	def __init__(self, view_mode=VIEW_HEX, parent=None):
		super(HexView, self).__init__(parent)

		self.setMouseTracking(False)
		self.setFocusPolicy(QtCore.Qt.StrongFocus)

		self.data_source = None
		self.data_pos = 0
		self.data = None

##		self.font_name = 'Fixedsys'
##		self.font_name = 'Segoe Script'
##		self.font_name = 'MV Boli'
		self.font_name = get_recommended_font()
		self.font_size = 10
		self.byte_num_per_line = 16
		self.byte_num_per_page = 0
		self.view_mode = view_mode
		self.selected_region_mode = HexView.SELECTED_REGION_HIDDEN

		self.cursor_pos = 0
		self.begin_selected_byte_pos = 0
		self.end_selected_byte_pos = 0
		self.selecting_begin_selected_byte_pos = 0
		self.selecting_end_selected_byte_pos = 0

		self.is_editing_half_byte = False

		self.line_height = []
		self.line_rect_list = []
		self.address_list = []

class HexEdit(QtGui.QFrame):

	@QtCore.pyqtSlot(int, int)
	def update_scroll_bar_range(self, minimum, maximum):
		self.vertical_scroll_bar.setMinimum(minimum)
		self.vertical_scroll_bar.setMaximum(maximum)

	@QtCore.pyqtSlot(int, int)
	def update_scroll_bar_step(self, single_step, page_step):
		self.vertical_scroll_bar.setSingleStep(single_step)
		self.vertical_scroll_bar.setPageStep(page_step)

	@QtCore.pyqtSlot(int)
	def update_scroll_bar(self, slider_position):
		self.vertical_scroll_bar.setTracking(False)
		self.vertical_scroll_bar.setSliderPosition(slider_position)
		self.vertical_scroll_bar.setTracking(True)

	def __init__(self, data_source=HexViewDataSource(), parent=None):
		super(HexEdit, self).__init__(parent)

		horizontal_layout = QtGui.QHBoxLayout(self)
		splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
		horizontal_spacer = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
		self.vertical_scroll_bar = QtGui.QScrollBar(QtCore.Qt.Vertical)

		self.address_view = AddressView()
		self.hex_view = HexView(HexView.VIEW_HEX)
		self.byte_view = HexView(HexView.VIEW_CHAR)

		self.vertical_scroll_bar.valueChanged.connect(self.hex_view.update_data_and_cursor_no_signal)
		self.vertical_scroll_bar.valueChanged.connect(self.byte_view.update_data_and_cursor_no_signal)

		self.hex_view.data_source_changed.connect(self.update_scroll_bar_range)
		self.hex_view.data_changed.connect(self.update_scroll_bar_step)
		self.hex_view.data_pos_changed.connect(self.update_scroll_bar)
		self.hex_view.data_pos_changed.connect(self.byte_view.update_data_pos_no_signal)
		self.hex_view.cursor_pos_changed.connect(self.byte_view.update_cursor_pos_no_signal)
		self.hex_view.selected_region_changed.connect(self.byte_view.update_selected_region_no_signal)
		self.hex_view.address_list_changed.connect(self.address_view.update_address_list)

		self.byte_view.data_pos_changed.connect(self.update_scroll_bar)
		self.byte_view.data_pos_changed.connect(self.hex_view.update_data_pos_no_signal)
		self.byte_view.cursor_pos_changed.connect(self.hex_view.update_cursor_pos_no_signal)
		self.byte_view.selected_region_changed.connect(self.hex_view.update_selected_region_no_signal)

		self.set_data_source(data_source)

		def assemble_frame(frame, name=''):
			f = QtGui.QFrame()
			l = QtGui.QVBoxLayout(f)
			l.addWidget(QtGui.QLabel(name))
			l.addWidget(frame)
			l.setStretch(1, 1)
			return f

		splitter.addWidget(assemble_frame(self.address_view, 'Address'))
		splitter.addWidget(assemble_frame(self.hex_view, 'Hex dump'))
		splitter.addWidget(assemble_frame(self.byte_view, 'ASCII'))

		horizontal_layout.addWidget(splitter)
		horizontal_layout.addItem(horizontal_spacer)
		horizontal_layout.addWidget(self.vertical_scroll_bar)

		self.address_view.setMinimumWidth(80)
		self.hex_view.setMinimumWidth(390)
		self.byte_view.setMinimumWidth(130)

	def set_data_source(self, data_source):
		self.hex_view.data_source = data_source
		self.byte_view.data_source = data_source
		self.hex_view.update_view()
		self.byte_view.update_view()

class AddressView(QtGui.QFrame):

	def paintEvent(self, event):
		super(AddressView, self).paintEvent(event)

		painter = QtGui.QPainter(self)
		painter.setFont(Qt.QFont(self.font_name, self.font_size))

		flag = QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop | QtCore.Qt.TextDontClip | QtCore.Qt.TextSingleLine
		line_height = painter.boundingRect(QtCore.QRect(), flag, 'f').height()

		painter.setPen(QtCore.Qt.black)

		for line_index, address in enumerate(self.address_list):
			line_x = 0
			line_y = line_index * line_height
			painter.drawText(QtCore.QRect(line_x, line_y, 0, 0), flag, self.address_format % address)

	@QtCore.pyqtSlot(list)
	def update_address_list(self, address_list):
		self.address_list = address_list
		self.update()

	def __init__(self, parent=None):
		super(AddressView, self).__init__(parent)

		self.address_list = []

		self.font_name = get_recommended_font()
		self.font_size = 10

		bits, linkage = platform.architecture()
		if not bits or bits == '32bit':
			self.address_format = '%08x'
		elif bits == '64bit':
			self.address_format = '%016x'
		else:
			raise

def get_recommended_font():
	recommended_font_list = {'Windows':'Fixedsys', 'Linux':'Monospace', 'Darwin':'Monaco'}
	try:
		return recommended_font_list[platform.system()]
	except:
		return ''

def main():
	app = QtGui.QApplication(sys.argv)
	hex_edit = HexEdit(HexViewFileSource('test.jpg'))
	hex_edit.resize(600, 300)
	hex_edit.setWindowTitle('HexEdit')
	hex_edit.show()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
