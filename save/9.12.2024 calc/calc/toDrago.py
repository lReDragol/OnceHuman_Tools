
#== библиотеки
from tkinter import *
from tkinter import ttk 

#== переменные
entry_ids = []      #-- список имен полей ввода
entry_maxnum = -1   #-- максимальный номер поля ввода
entries = {}        #-- словарь полей ввода
entry_row = 0       #-- строка поля ввода

label_ids = []      #-- список имен labels
label_maxnum = -1   #-- максимальный номер label
labels = {}         #-- словарь labels

#== форма и панели
root = Tk()
panel1 = Frame(root, padx = 5)
panel1.pack()


# заголовок
ttk.Label(panel1, text = "Calculator Once Human").grid(row = 0, column = 0, columnspan = 2)
cur_row = 1

# текстовое поле для строки
label_damage = Label(panel1, text='Damage:', padx=5, font='Arial 30').grid(row = cur_row, column = 0, columnspan = 2)
cur_row += 1

txt_mess = Label(panel1, text = '', font='ArialBold 30')
txt_mess.grid(row = cur_row, column = 0, columnspan = 2)
cur_row+= 1


##-- кнопка Собрать текст из слов -> "РАССЧИТАТЬ"
def fnc_jointext():
    """Собрать все цифры из полей ввода"""
    lst_words = []
    for entry_id in entry_ids:
        entry = entries[entry_id][0]
        cur_text = entry.get()
        lst_words.append(cur_text)
    #-- записать их в текстовое поле

    wep_att = weapon_attack.get()
    for bonus in lst_words:
        bonus_float = 1 + float(bonus) / 100
        wep_att *=  bonus_float
    wep_att = round(wep_att, 2)
    text = str(wep_att)

    txt_mess.config(text = text)

ttk.Button(panel1, text = "Calculate", command = fnc_jointext).grid(row = cur_row, column = 0)

cur_row += 1


##-- метки номера текущего поля ввода

lbl_num = ttk.Label(panel1, text = "-1")
lbl_left_num = ttk.Label(panel1, text = "-1")

cur_row += 1


##-- значение текущего поля ввода
lab_cur_entry = ttk.Label(panel1, text = "cur entry:")

cur_val = IntVar()
cur_lab = IntVar()
cur_entry = ttk.Entry(panel1, textvariable=cur_val)
cur_label = ttk.Label(panel1, textvariable=cur_lab)

cur_row += 1

##--Атака оружия
ttk.Label(panel1, text = "Base DMG: ").grid(row = cur_row, column = 0)
weapon_attack = IntVar()
weapon_attack_entry = ttk.Entry(panel1, textvariable=weapon_attack)
weapon_attack_entry.grid(row = cur_row, column = 1)
cur_row += 1



##-- кнопка Добавить окно мультипликатора

###-- обработчик щелчка по динамическому полю с параметром
def set_entrynum(event, entry_id):
    print("entry_id = ",entry_id)
    lbl_num["text"] = entry_id[3:]

    print("label_id = ",entry_id) #2
    lbl_left_num["text"] = entry_id[3:] #2

###-- обработчик кнопки добавления динамического поля
def fnc_addentry():
    global entries, entry_ids, entry_maxnum, labels, label_ids, label_maxnum

    entry_maxnum += 1
    label_maxnum += 1 #2
    entry_id = "ent"+str(entry_maxnum)
    label_id = "lab"+str(label_maxnum) #2
    entry_ids.append( entry_id )
    label_ids.append( label_id ) #2

    print(entry_id)
    print(label_id) #2
    lbl_num["text"] = entry_id[3:]
    lbl_left_num["text"] = label_id[3:]  #2

    entry_val = IntVar()
    label_val = IntVar() #2
    entry = ttk.Entry(pnl_entry, textvariable=entry_val)
    label = ttk.Label(pnl_label, textvariable=label_val) #2
    entry_val.set(cur_val.get())
    label_val.set(cur_lab.get()) #2
    
    #entry.bind("<Button-1>", event_info)
    entry.bind("<Button-1>", lambda event, arg = entry_id: set_entrynum(event, arg))

    entry_row = entry_maxnum
    label_row = label_maxnum #2
    entry.grid(row = entry_row, sticky=E)
    label.grid(row = label_row, sticky=W) #2
    entries[entry_id] = (entry, entry_val)
    labels[entry_id] = (label, label_val) #2
    lbl_num["text"] = str(len(entries)-1)
    lbl_left_num["text"] = str(len(labels)-1) #2
    
ttk.Button(panel1, text = "add multiplier", command = fnc_addentry).grid(row = cur_row, column = 1)



##-- функция обмена значениями двух элементов
def change_vals( first_num, second_num):
    first_id = "ent"+ str(first_num);  second_id = "ent"+ str(second_num)
    first_val,  second_val = entries[first_id][1], entries[second_id][1]
    first_text, second_text = first_val.get(), second_val.get()
    first_val.set(second_text); second_val.set(first_text)

##-- кнопка Удалить текущее поле ввода
def fnc_delentry():
    global entries, entry_maxnum, entry_ids, labels, label_maxnum, label_ids
    #-- сдвинуть значения хвоста вверх
    cur_num = int(lbl_num["text"])
    if cur_num < 0:  return
    
    for num in range(cur_num, entry_maxnum):
        change_vals( num, num+1)
    #-- удалить последний элемент
    entry_id = "ent"+str(entry_maxnum)
    label_id = "lab"+str(label_maxnum) #2
    entry_ids = entry_ids[:-1]
    label_ids = label_ids[:-1] #2
    entry = entries[ entry_id ][0]
    #label = labels[ label_id ][0] #2
    entry.destroy()
    #label.destroy() #2
    
    #-- скорректировать число элементов
    entry_maxnum -=1
    label_maxnum -=1
    lbl_num["text"] = entry_maxnum
    lbl_left_num["text"] = label_maxnum
        
ttk.Button(panel1, text = "del multiplier", command = fnc_delentry).grid(row = cur_row, column = 0)

cur_row += 1



##-- панель для динамических полей ввода 
pnl_entry = Frame(panel1)
pnl_entry.grid(row = cur_row, column = 1)
pnl_label = Frame(panel1)
pnl_label.grid(row = cur_row, column = 0)

#== запуск в работу
mainloop()
