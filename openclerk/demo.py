"""Portable synthetic native Tk target for Windows and Linux desktop tests."""
import json
import os
import sys
from pathlib import Path


def main():
    import tkinter as tk
    root=tk.Tk(className='OpenClerkDemo')
    root.title('OpenClerk Clinic · Synthetic desktop test')
    root.geometry('960x650+160+100');root.resizable(False,False);root.configure(bg='#f8faf6')
    def label(text,x,y,size=14,bold=False):
        widget=tk.Label(root,text=text,font=('Helvetica',size,'bold' if bold else 'normal'),bg='#f8faf6',fg='#234b3c',anchor='w')
        widget.place(x=x,y=y);return widget
    label('OPENCLERK / CLINIC',32,32,12,True)
    label('Referral workspace',32,74,29,True)
    label('SYNTHETIC DATA ONLY · Native desktop app · No EHR or payer connection',32,126,12)
    label('TEST-REF-001',32,205,18,True);label('Test Patient One',32,245,17,True)
    label('Record: SYN-001',32,280);label('Specialty: Cardiology',32,315)
    label('Referral status',32,405,13,True);status=label('Ready to schedule',32,445,18,True)
    label('Prepare an appointment',344,195,20,True);label('Provider',344,239,13,True)
    provider=tk.IntVar(value=0);slot=tk.IntVar(value=0)
    a=tk.Radiobutton(root,text='Test Provider A',variable=provider,value=1,bg='#f8faf6',font=('Helvetica',14))
    b=tk.Radiobutton(root,text='Test Provider B',variable=provider,value=2,bg='#f8faf6',font=('Helvetica',14))
    a.place(x=344,y=275,width=250,height=34);b.place(x=610,y=275,width=250,height=34)
    label('Appointment slot',344,326,13,True)
    sa=tk.Radiobutton(root,text='Synthetic slot A · 09:00',variable=slot,value=1,bg='#f8faf6',font=('Helvetica',13))
    sb=tk.Radiobutton(root,text='Synthetic slot B · 10:30',variable=slot,value=2,bg='#f8faf6',font=('Helvetica',13))
    sa.place(x=344,y=360,width=260,height=34);sb.place(x=610,y=360,width=260,height=34)
    label('Administrative note',344,410,13,True)
    note=tk.Entry(root,font=('Helvetica',14),insertontime=0);note.place(x=344,y=450,width=530,height=34)
    activity=label('No appointment has been saved.',344,560,12)
    booked=False
    def save():
        nonlocal booked
        root.focus_set()
        if booked:activity.config(text='Duplicate blocked: this referral already has an appointment.');return
        if not provider.get() or not slot.get():activity.config(text='Select a provider and an appointment slot before saving.');return
        booked=True;status.config(text='Appointment booked');activity.config(text='Saved SYN-APT-001 · Synthetic slot '+('A' if slot.get()==1 else 'B'))
        path=os.environ.get('OPENCLERK_DEMO_RESULT')
        if path:
            Path(path).write_text(json.dumps({'synthetic':True,'appointment_id':'SYN-APT-001','provider':provider.get(),'slot':slot.get(),'note':note.get()}))
    def reset():
        nonlocal booked
        booked=False;provider.set(0);slot.set(0);note.delete(0,tk.END);root.focus_set()
        status.config(text='Ready to schedule');activity.config(text='No appointment has been saved.')
    tk.Button(root,text='Save appointment',command=save).place(x=344,y=510,width=220,height=34)
    tk.Button(root,text='Reset test',command=reset).place(x=744,y=510,width=130,height=34)
    label('This workspace has no clinical decisions or real patient information.',32,618,11)
    def advertise_x11_pid():
        # Tk does not consistently publish its PID. Set it only on this fixture's managed ancestor.
        if not sys.platform.startswith('linux'): return
        try:
            from Xlib import display, X, Xatom
            connection=display.Display();desktop=connection.screen().root
            prop=desktop.get_full_property(connection.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType)
            clients=set(int(value) for value in ([] if prop is None else prop.value))
            window=connection.create_resource_object('window',root.winfo_id())
            for _ in range(6):
                if window.id in clients:
                    window.change_property(connection.intern_atom('_NET_WM_PID'),Xatom.CARDINAL,32,[os.getpid()]);connection.sync();break
                parent=window.query_tree().parent
                if not parent or parent.id==desktop.id:break
                window=parent
            connection.close()
        except Exception:pass
    root.after(100,root.focus_set);root.after(200,advertise_x11_pid);root.mainloop()


if __name__=='__main__':main()
