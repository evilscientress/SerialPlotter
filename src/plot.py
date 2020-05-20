import argparse
import os
import os.path
import sys

from PyQt5 import QtChart, QtCore, QtGui, QtSerialPort, QtWidgets
from PyQt5.QtCore import Qt


class SerialPlotter(QtWidgets.QMainWindow):

    def __init__(self, port, baud=115200, num_values=255, **kwargs):
        super(SerialPlotter, self).__init__(**kwargs)
        self._serial_port = port
        self._serial_port_baud = baud
        self._num_values = num_values

        self.series = []
        self.data = []

        # set up chart
        self.setWindowTitle('Serial Plotter')
        self.setContentsMargins(0, 0, 0, 0)
        self.chart = QtChart.QChart()
        self.chart.setTheme(QtChart.QChart.ChartThemeDark)
        # remove the annoying white border
        self.chart.layout().setContentsMargins(0, 0, 0, 0)
        self.chart.setBackgroundRoundness(0)

        # set up chart view
        self.chart_view = QtChart.QChartView(self.chart)
        self.chart_view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.chart_view.setMinimumSize(800, 600)

        # set up axis
        self.x_axis = QtChart.QValueAxis()
        self.x_axis.setRange(0, self._num_values)
        self.x_axis.setTitleText('Samples')
        self.x_axis.setLabelFormat('%i')
        self.y_axis = QtChart.QValueAxis()
        self.y_axis.setRange(0, 1023)
        self.y_axis.setTitleText('Values')
        self.chart.addAxis(self.x_axis, Qt.AlignBottom)
        self.chart.addAxis(self.y_axis, Qt.AlignLeft)

        self.setCentralWidget(self.chart_view)

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

    def add_series(self, name=None):
        # add a series
        series = QtChart.QLineSeries()
        self.chart.addSeries(series)
        series.attachAxis(self.x_axis)
        series.attachAxis(self.y_axis)
        series.setUseOpenGL(True)
        if name:
            series.setName(name)
        self.series.append(series)

    def append_data(self, new_data, auto_update=True):
        num_elements = len(new_data)

        if len(self.data) < num_elements:
            if len(self.data) >= 1:
                # we need to pad the newly added lines
                padded = [None] * len(self.data[0])
                for i in range(len(self.data) - num_elements):
                    self.data.append(padded.copy())
            else:
                for i in range(num_elements):
                    self.data.append([])

        num_values_current = len(self.data[0])
        for i in range(num_elements):
            if num_values_current >= self._num_values:
                self.data[i] = self.data[i][1:] + [new_data[i]]
            else:
                self.data[i].append(new_data[i])

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
        if not self.data:
            return
        # add all series not yet present
        for i in range(len(self.series), len(self.data)):
            self.add_series(name='Ch %d' % i)

        # update the series data
        for i in range(len(self.series)):
            self.series[i].replace([QtCore.QPoint(j, self.data[i][j]) for j in range(len(self.data[i]))])


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
