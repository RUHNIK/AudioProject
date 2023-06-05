import PySimpleGUI as sg
import pyaudio
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import wave
import random

# \\ -------- CONSTS -------- //

# SOUND CONSTS
CHUNK = 1024
RATE = 44100
TIMEOUT = 10

# PyPlot CONSTS:
OX_LIM = 44100
OY_LIM = 40000

# VARS CONSTS:
_VARS = {'window': False,
         'visual': False,
         'stream': False,
         'fig_agg': False,
         'pltFig': False,
         'pltAx': False,
         'fig_agg_VS': False,
         'pltFig_VS': False,
         'pltAx_VS': False,
         'xData': False,
         'line': False,
         'audioData': False,
         'temp': False,
         'record': False,
         'sample': 0,
         'flag': False,
         'filename': 'Record',
         'st_start': 0,
         'paused': False,
         'sec': 0,
         'grad_lines': np.array(['#ffffff' for x in range(450)]),
         'fireclick': 0}

# // -------- CONSTS -------- \\

# \\ -------- INITS -------- //

# pysimpleGUI INIT:
ButtonFont = ('Any', 16)
TextFont = ('Any', 12)
TimeFont = ('OCR-A BT', 20)
sg.theme('BrownBlue')
layout = [[sg.Canvas(key='-CANVAS-')],
          [sg.ProgressBar(40000, orientation='h',
                          size=(60, 20), key='-MAX-')],
          [sg.ProgressBar(40000, orientation='h',
                          size=(60, 20), key='-PROG-')],
          [sg.Button('Listen', font=ButtonFont),
           sg.Button('Stop', font=ButtonFont, disabled=True),
           sg.Button('Start record', font=ButtonFont, disabled=True),
           sg.Button('Pause record', font=ButtonFont, disabled=True, key='-PAUSE|CONTINUE-', size=(18, 1)),
           sg.Button('Stop record', font=ButtonFont, disabled=True),
           sg.Text('00:00', font=TimeFont, key='-TIME-'),
           sg.Button('Record settings', font=ButtonFont),
           sg.Button('Visual', font=ButtonFont)],
          [sg.Button('Exit', font=ButtonFont)]]
_VARS['window'] = sg.Window('Microphone Waveform',                 # создание соновного окна
                            layout, finalize=True,
                            location=(400, 100))

# PyAudio INIT:
pAud = pyaudio.PyAudio()                                           # создание записывающего объекта

# Pyplot INIT:
plt.ion()                                                          # включение режима анимации у графика
plt.style.use('ggplot')                                            # выбор стиля графика

_VARS['pltFig'] = plt.figure(num=0, figsize=(10, 5))
_VARS['pltAx'] = _VARS['pltFig'].add_subplot()
_VARS['pltAx'].set_xlim(0, OX_LIM)
_VARS['pltAx'].set_ylim(-OY_LIM, OY_LIM)

# _VARS INIT:
_VARS['xData'] = np.linspace(0, RATE, num=RATE, dtype=int)
_VARS['audioData'] = np.zeros(RATE)
_VARS['temp'] = np.zeros(CHUNK)

# // -------- INITS -------- \\

# \\ -------- FUNCTIONS -------- //

# _VARS FUNCTIONS:
def update_VARS():
    # "склейка" аудиоданных
    _VARS['audioData'] = np.concatenate((_VARS['audioData'][CHUNK:_VARS['audioData'].size], _VARS['temp']))
    # вычисление максимумальной амплитуды на всём промежутке графика и в "новой" его части
    max_audioData = np.amax(_VARS['audioData'])
    max_temp = np.amax(_VARS['temp'])
    # частное амплитуд с учётом модификатора (количество кликов 'Fire!) вляет на яркость случайного цвета
    add_grad = 0
    if max_temp != 0:
        add_grad = (max_temp + 1000 * _VARS['fireclick']) / (max_audioData + 1000 * _VARS['fireclick'])
    # "затухание" графика в окне Visual
    if _VARS['fireclick'] > 0:
        _VARS['fireclick'] = _VARS['fireclick'] - 1
    # обновление столбцов загрузки, отображающих амплитуды звука (громкость)
    _VARS['window']['-MAX-'].update(max_audioData)
    _VARS['window']['-PROG-'].update(max_temp)
    # вычисление цветов для новой части градиента (с1 обеспечивает плавный переход на стыках цветов)
    a = np.array(['#ffffff' for x in range(90)])
    c1 = np.array([mpl.colors.to_rgb(_VARS['grad_lines'][_VARS['grad_lines'].size - 1])])
    c2 = np.fabs(np.array([random.random() * add_grad, random.random() * add_grad, random.random() * add_grad]))
    for x in range(90):
        a[x] = colorFader(c1, c2, x / 89)
    # склейка данных для графика градиентов
    _VARS['grad_lines'] = np.concatenate((_VARS['grad_lines'][90:_VARS['grad_lines'].size], a))


# PyPlot FUNCTIONS:
def bind_canvas_and_fig(canvas, figure):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg


def drawPlot(fig):
    fig.canvas.draw()
    fig.canvas.flush_events()


def updatePlot(win):
    if win == 0:
        _VARS['line'].set_ydata(_VARS['audioData'])
    else:
        # поскольку у графика Visual нет "актёра", его приходится перерисовывать полностью
        # единственно, что тут можно сделать -- вычислять лишь чать данных, а не пресчитывать все
        # это связано с тем, что размер audioData > CHUNK, т.е. порция данных, считываемая через микрофон
        # менбше всей отображаемой картины, что является следствием желания сделать не просто динамически
        # изменяющуюся анимацию волны и градиента, но и отобразить их смену и развитие с течением времени.
        _VARS['pltAx_VS'].cla()
        for x in range(450):
            _VARS['pltAx_VS'].axvline(x, color=_VARS['grad_lines'][x], linewidth=6)


def create_actor(win):
    if win == 0:
        # создание актёра-линии для основного окна и связывания графика с полотном
        _VARS['line'], = _VARS['pltAx'].plot(_VARS['xData'], _VARS['audioData'], '--g')
        _VARS['fig_agg'] = bind_canvas_and_fig(_VARS['window']['-CANVAS-'].TKCanvas, _VARS['pltFig'])
    else:
        # связывание графика с полотном в окне Visual
        _VARS['fig_agg_VS'] = bind_canvas_and_fig(_VARS['visual']['-CANVAS-'].TKCanvas, _VARS['pltFig_VS'])


# PyAudio FUNCTIONS:
def stop():
    if _VARS['stream']:
        _VARS['stream'].stop_stream()
        _VARS['stream'].close()
        _VARS['window']['-MAX-'].update(0)
        _VARS['window']['-PROG-'].update(0)
        _VARS['window']['Stop'].Update(disabled=True)
        _VARS['window']['Listen'].Update(disabled=False)
        _VARS['temp'] = np.zeros(CHUNK)
    _VARS['window']['Start record'].Update(disabled=True)
    _VARS['window']['Record settings'].Update(disabled=False)


def callback(in_data, frame_count, time_info, status):
    # функция callback вызывается после записи каждого нового кусочка размером CHUNK для обработки
    _VARS['temp'] = np.frombuffer(in_data, dtype=np.int16)
    # если ЗАПИСЬ не на паузе и идёт, записывает
    if _VARS['record'] and not _VARS['paused']:
        _VARS['record'].writeframes(in_data)
    return in_data, pyaudio.paContinue


def listen():
    _VARS['window']['Stop'].Update(disabled=False)
    _VARS['window']['Listen'].Update(disabled=True)
    _VARS['stream'] = pAud.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=RATE,
                                input=True,
                                frames_per_buffer=CHUNK,
                                stream_callback=callback)
    _VARS['stream'].start_stream()
    _VARS['window']['Start record'].Update(disabled=False)
    _VARS['window']['Record settings'].Update(disabled=True)


# Record FUNCTIONS:
def set_filename():
    filename = _VARS['filename']
    # определяет правило записи по кусочкам
    if _VARS['flag']:
        _VARS['sample'] = _VARS['sample'] + 1
        filename += ' ' + str(_VARS['sample'])
    else:
        _VARS['sample'] = 0
    filename += '.wav'
    return filename


def start_record():
    _VARS['window']['Start record'].Update(disabled=True)
    _VARS['window']['-PAUSE|CONTINUE-'].Update(disabled=False)
    _VARS['window']['Stop record'].Update(disabled=False)
    filename = set_filename()
    _VARS['record'] = wave.open(filename, 'wb')
    _VARS['record'].setnchannels(1)
    _VARS['record'].setsampwidth(pAud.get_sample_size(pyaudio.paInt16))
    _VARS['record'].setframerate(RATE)


def pc_record():
    _VARS['paused'] = not _VARS['paused']
    if _VARS['paused']:
        _VARS['sec'] = time.time() - _VARS['st_start'] + _VARS['sec']
        _VARS['window']['-PAUSE|CONTINUE-'].update('Continue record')
    else:
        _VARS['window']['-PAUSE|CONTINUE-'].update('Pause record')
        start_stopwatch()


def end_record():
    if _VARS['record']:
        _VARS['record'].close()
        _VARS['record'] = False
    _VARS['window']['Start record'].Update(disabled=False)
    _VARS['window']['-PAUSE|CONTINUE-'].Update('Pause record', disabled=True)
    _VARS['window']['Stop record'].Update(disabled=True)


def record_settings():
    _VARS['window'].hide()
    rec_layout = [[sg.Text('Record name:', font=TextFont),
                   sg.InputText(default_text=_VARS['filename'], font=TextFont, key='-INPUT-'),
                   sg.Checkbox('Sample record', default=_VARS['flag'], key="-CHECKBOX-")],
                  [sg.Button('Save', font=ButtonFont), sg.Button('Exit', font=ButtonFont)]]
    rec_window = sg.Window('Record settings', rec_layout)
    # это БЛОКИРУЮЩЕЕ окно, его невозможно вызвать в процессе записи или прослушивания,
    # оно останавливает работу основного окна для указания настроек записи
    while True:
        rec_event, rec_values = rec_window.read()
        if rec_event == 'Exit' or rec_event == sg.WIN_CLOSED:
            break
        if rec_event == 'Save':
            _VARS['filename'] = rec_values['-INPUT-']
            _VARS['flag'] = rec_values['-CHECKBOX-']
    rec_window.close()
    _VARS['window'].un_hide()


# Stopwatch FUNCTIONS:                      в этом сегменте описывается работа секундомера
def start_stopwatch():
    _VARS['st_start'] = time.time()


def curr_stopwatch():
    if _VARS['record']:
        if not _VARS['paused']:
            _VARS['window']['-TIME-'].update('{:05.2f}'.format(time.time() - _VARS['st_start'] + _VARS['sec']))
        else:
            _VARS['window']['-TIME-'].update('{:05.2f}'.format(_VARS['sec']))


def reset_stopwatch():
    _VARS['paused'] = False
    _VARS['sec'] = 0
    _VARS['window']['-TIME-'].update('{:05.2f}'.format(_VARS['sec']))


# Gradient FUNCTIONS:
# описание окна, в котором рисуется градиент
def visual():
    vs_layout = [[sg.Canvas(key='-CANVAS-'), sg.Button('Fire!', font=ButtonFont)],
                 [sg.Button('Exit', font=ButtonFont)]]
    _VARS['visual'] = sg.Window('Waveform Visualization', vs_layout, finalize=True)

    _VARS['pltFig_VS'] = plt.figure(num=1, figsize=(5, 5))
    _VARS['pltAx_VS'] = _VARS['pltFig_VS'].add_subplot()
    _VARS['pltAx_VS'].set_xlim(0, 50)
    _VARS['pltAx_VS'].set_ylim(-2, 2)

# считает значение линейного градиента в точке
def colorFader(c1,c2,mix=0):
    return mpl.colors.to_hex((1-mix)*c1 + mix*c2)


# // -------- FUNCTIONS -------- \\

create_actor(0)

# MAIN LOOP
while True:
    event, values = _VARS['window'].read(timeout=TIMEOUT)
    if event == sg.WIN_CLOSED or event == 'Exit':
        end_record()
        stop()
        pAud.terminate()
        plt.ioff()
        break
    if event == 'Listen':
        listen()
    elif event == 'Stop':
        end_record()
        stop()
        reset_stopwatch()
    elif event == 'Start record':
        start_record()
        reset_stopwatch()
        start_stopwatch()
    elif event == '-PAUSE|CONTINUE-':
        pc_record()
    elif event == 'Stop record':
        end_record()
    elif event == 'Record settings':
        record_settings()
    elif event == 'Visual':
        visual()
        create_actor(1)
    elif _VARS['audioData'].size != 0:
        update_VARS()
        updatePlot(0)
        drawPlot(_VARS['pltFig'])
        curr_stopwatch()

    if _VARS['visual']:
        vs_event, vs_values = _VARS['visual'].read(timeout=TIMEOUT)
        if vs_event == sg.WIN_CLOSED or vs_event == 'Exit':
            _VARS['visual'].close()
            _VARS['visual'] = False
        elif vs_event == 'Fire!':
            _VARS['fireclick'] = _VARS['fireclick'] + 5
        else:
            updatePlot(1)
            drawPlot(_VARS['pltFig_VS'])

_VARS['visual'].close()
_VARS['window'].close()
