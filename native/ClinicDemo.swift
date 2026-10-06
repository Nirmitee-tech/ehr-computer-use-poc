import AppKit

final class StableFieldEditor: NSTextView {
    override func drawInsertionPoint(in rect: NSRect, color: NSColor, turnedOn flag: Bool) {}
    override func updateInsertionPointStateAndRestartTimer(_ restartFlag: Bool) {}
}

final class DemoDelegate: NSObject, NSApplicationDelegate, NSTextFieldDelegate, NSWindowDelegate {
    var window: NSWindow!
    var status: NSTextField!
    var activity: NSTextField!
    var note: NSTextField!
    var providerA: NSButton!
    var providerB: NSButton!
    var slotA: NSButton!
    var slotB: NSButton!
    var providerIndex = 0
    var slotIndex = 0
    var booked = false
    let stableEditor = StableFieldEditor(frame: .zero)
    let teal = NSColor(calibratedRed: 0.08, green: 0.38, blue: 0.35, alpha: 1)
    func label(_ text: String, _ x: CGFloat, _ y: CGFloat, _ width: CGFloat, _ size: CGFloat = 15, _ bold: Bool = false) -> NSTextField {
        let field = NSTextField(labelWithString: text)
        field.frame = NSRect(x: x, y: y, width: width, height: size > 22 ? 45 : 30)
        field.font = bold ? .boldSystemFont(ofSize: size) : .systemFont(ofSize: size)
        field.textColor = .labelColor
        window.contentView!.addSubview(field)
        return field
    }
    func button(_ title: String, _ x: CGFloat, _ y: CGFloat, _ width: CGFloat, _ selector: Selector) {
        let control = NSButton(title: title, target: self, action: selector)
        control.frame = NSRect(x: x, y: y, width: width, height: 38)
        control.bezelStyle = .rounded
        window.contentView!.addSubview(control)
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(contentRect: NSRect(x: 160, y: 150, width: 960, height: 650), styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.delegate = self
        window.title = "OpenClerk Clinic · Synthetic desktop test"
        window.contentView!.wantsLayer = true
        window.contentView!.layer?.backgroundColor = NSColor.windowBackgroundColor.cgColor
        _ = label("OPENCLERK / CLINIC", 32, 590, 600, 13, true)
        _ = label("Referral workspace", 32, 539, 800, 30, true)
        let banner = label("SYNTHETIC DATA ONLY · Native macOS app · No EHR or payer connection", 32, 502, 880, 13)
        banner.textColor = teal
        _ = label("REFERRAL", 32, 451, 180, 12, true)
        _ = label("TEST-REF-001", 32, 414, 210, 19, true)
        _ = label("Test Patient One", 32, 377, 240, 18, true)
        _ = label("Record: SYN-001", 32, 347, 240, 14)
        _ = label("Specialty: Cardiology", 32, 315, 240, 14)
        _ = label("Routine scheduling only", 32, 283, 260, 14)
        _ = label("Referral status", 32, 230, 240, 13, true)
        status = label("Ready to schedule", 32, 196, 270, 18, true)
        status.textColor = teal
        _ = label("Prepare an appointment", 344, 450, 570, 21, true)
        _ = label("Provider", 344, 412, 230, 13, true)
        providerA = NSButton(radioButtonWithTitle: "Test Provider A", target: self, action: #selector(selectProviderA))
        providerB = NSButton(radioButtonWithTitle: "Test Provider B", target: self, action: #selector(selectProviderB))
        providerA.frame = NSRect(x: 344, y: 370, width: 250, height: 34)
        providerB.frame = NSRect(x: 610, y: 370, width: 250, height: 34)
        window.contentView!.addSubview(providerA); window.contentView!.addSubview(providerB)
        _ = label("Appointment slot", 344, 329, 230, 13, true)
        slotA = NSButton(radioButtonWithTitle: "Synthetic slot A · 09:00", target: self, action: #selector(selectSlotA))
        slotB = NSButton(radioButtonWithTitle: "Synthetic slot B · 10:30", target: self, action: #selector(selectSlotB))
        slotA.frame = NSRect(x: 344, y: 287, width: 260, height: 34)
        slotB.frame = NSRect(x: 610, y: 287, width: 260, height: 34)
        window.contentView!.addSubview(slotA); window.contentView!.addSubview(slotB)
        _ = label("Administrative note", 344, 247, 280, 13, true)
        note = NSTextField(frame: NSRect(x: 344, y: 197, width: 530, height: 36))
        note.placeholderString = "Enter a test scheduling note"
        note.font = .systemFont(ofSize: 15)
        note.delegate = self
        window.contentView!.addSubview(note)
        button("Save appointment", 344, 138, 220, #selector(save))
        button("Reset test", 744, 138, 130, #selector(reset))
        activity = label("No appointment has been saved.", 344, 87, 570, 14)
        _ = label("This workspace has no clinical decisions or real patient information.", 32, 24, 880, 12)
        window.initialFirstResponder = nil
        window.makeKeyAndOrderFront(nil)
        window.makeFirstResponder(nil)
        NSApp.activate()
    }
    func windowWillReturnFieldEditor(_ sender: NSWindow, to client: Any?) -> Any? {
        guard let field = client as? NSTextField, field === note else { return nil }
        stableEditor.isFieldEditor = true
        return stableEditor
    }
    func controlTextDidBeginEditing(_ notification: Notification) {
        // Keep fixture pixels stable so freshness tests exercise data changes rather than a blinking caret.
        (window.fieldEditor(true, for: note) as? NSTextView)?.insertionPointColor = .clear
    }
    @objc func selectProviderA() { providerIndex = 1; providerA.state = .on; providerB.state = .off }
    @objc func selectProviderB() { providerIndex = 2; providerA.state = .off; providerB.state = .on }
    @objc func selectSlotA() { slotIndex = 1; slotA.state = .on; slotB.state = .off }
    @objc func selectSlotB() { slotIndex = 2; slotA.state = .off; slotB.state = .on }
    @objc func save() {
        window.makeFirstResponder(nil)
        guard !booked else { activity.stringValue = "Duplicate blocked: this test referral already has an appointment."; return }
        guard providerIndex > 0, slotIndex > 0 else { activity.stringValue = "Select a provider and an appointment slot before saving."; return }
        booked = true
        status.stringValue = "Appointment booked"
        activity.stringValue = "Saved SYN-APT-001 · " + (slotIndex == 1 ? slotA.title : slotB.title)
        if let path = ProcessInfo.processInfo.environment["OPENCLERK_DEMO_RESULT"] {
            let result: [String: Any] = ["synthetic": true, "appointment_id": "SYN-APT-001", "provider": providerIndex == 1 ? providerA.title : providerB.title, "slot": slotIndex == 1 ? slotA.title : slotB.title, "note": note.stringValue]
            try? JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]).write(to: URL(fileURLWithPath: path), options: .atomic)
        }
    }
    @objc func reset() {
        window.makeFirstResponder(nil); booked = false
        status.stringValue = "Ready to schedule"; activity.stringValue = "No appointment has been saved."
        providerIndex = 0; slotIndex = 0
        providerA.state = .off; providerB.state = .off; slotA.state = .off; slotB.state = .off; note.stringValue = ""
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}
let app = NSApplication.shared
let delegate = DemoDelegate()
app.setActivationPolicy(.regular)
app.delegate = delegate
app.run()
