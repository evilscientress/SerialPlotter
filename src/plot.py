import argparse
import os
import os.path
import sys

import matplotlib
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtSerialPort, QtWidgets

matplotlib.use('qt5agg')
plt.style.use('fivethirtyeight')


class SerialPlotter(QtWidgets.QMainWindow):

    def __init__(self, port, baud=115200, num_values=255, **kwargs):
        super(SerialPlotter, self).__init__(**kwargs)
        self._serial_port = port
        self._serial_port_baud = baud
        self._num_values = num_values

        self.lines = []
        self.data = []

        self.setWindowTitle('Serial Plotter')

        # Create the maptlotlib FigureCanvas object,
        # and define a single set of axes as self._axes.
        self._figure = Figure()
        self._axes = self._figure.add_subplot(111)
        self._axes: Axes
        self._axes.set_xlabel('Samples')
        self._axes.set_ylabel('Values')
        self._axes.set_xlim(0, self._num_values)
        self._axes.set_ylim(0, 1024)
        self.lines.append(self._axes.plot([], [], label='Ch 0')[0])
        self._canvas = FigureCanvasQTAgg(self._figure)

        # Create toolbar, passing _canvas as first parament, parent (self, the SerialPlotter) as second.
        toolbar = NavigationToolbar2QT(self._canvas, self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(self._canvas)

        # Create a placeholder widget to hold our toolbar and _canvas.
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        # Setup the serial port
        self.serial = QtSerialPort.QSerialPort(
            self._serial_port,
            baudRate=self._serial_port_baud,
            readyRead=self.on_serial_ready_read,
        )
        if not self.serial.open(QtCore.QIODevice.ReadWrite):
            print('can\'t open serial port')
            sys.exit(1)

        self.show()

    def append_data(self, new_data, auto_update=True):
        num_elements = len(new_data)

        if len(self.data) < num_elements:
            """
            if len(self.data) >= 1:
                # we need to pad the newly added lines
                padded = [None] * len(self.data[0])
                for i in range(len(self.data) - num_elements):
                    self.data.append(padded.copy())
            else:
                for i in range(num_elements):
                    self.data.append([])
            """
            for i in range(num_elements - len(self.data)):
                self.data.append(np.zeros(self._num_values))

        """
        num_values_current = len(self.data[0])
        for i in range(num_elements):
            if num_values_current >= self._num_values:
                self.data[i] = self.data[i][1:] + [new_data[i]]
            else:
                self.data[i].append(new_data[i])
        """
        for i in range(len(self.data)):
            dataset = np.roll(self.data[i], -1)
            dataset: np.ndarray
            dataset[-1] = new_data[i]
            self.data[i] = dataset

        if auto_update:
            self.update_plot()

    @QtCore.pyqtSlot()
    def on_serial_ready_read(self):
        while self.serial.canReadLine():
            line = self.serial.readLine().data().decode().strip()
            data = line.split()
            if '.' in line:
                data = list([float(i) for i in data])
            else:
                data = list([int(i) for i in data])

            self.append_data(data)

    @QtCore.pyqtSlot()
    def update_plot(self):
        if self.lines:
            # We have a reference, we can use it to update the data for those lines.
            num_values_current = len(self.data[0])
            for i in range(len(self.lines)):
                line = self.lines[i]
                if num_values_current == len(line.get_xdata()):
                    line.set_ydata(self.data[i])
                else:
                    line.set_data(range(num_values_current), self.data[i])

        # add all lines not yet present
        lines_added = False
        for i in range(len(self.lines), len(self.data)):
            print('adding new line')
            self.lines.append(self._axes.plot(self.data[i], label=('Ch %d' % i))[0])
            lines_added = True

        if lines_added:
            self._axes.legend(loc='upper left')

        # Trigger the _canvas to update and redraw.
        self._canvas.draw()


def check_serial_port(port):
    port = os.path.abspath(port)
    if not os.path.exists(port):
        raise argparse.ArgumentTypeError('%s does not exist' % port)
    if not os.access(port, os.R_OK + os.W_OK):
        raise argparse.ArgumentTypeError('%s is not read/write able' % port)
    return port


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('port', help='The serial port to listen to for data to plot', type=check_serial_port)
    parser.add_argument('-b', '--baud', help='The baud rate for the serial port', default=115200, type=int)
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    w = SerialPlotter(args.port)
    sys.exit(app.exec_())
