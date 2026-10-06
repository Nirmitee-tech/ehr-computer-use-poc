import AppKit
import CoreGraphics
import ScreenCaptureKit
import Vision
import CryptoKit

struct BridgeError: Error { let message: String }
func fail(_ message: String) throws -> Never { throw BridgeError(message: message) }
func emit(_ value: [String: Any]) { let data = try! JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]); print(String(data: data, encoding: .utf8)!); fflush(stdout) }
func boundsJSON(_ rect: CGRect) -> [String: Double] { ["x": rect.origin.x, "y": rect.origin.y, "width": rect.width, "height": rect.height] }
func target(_ bundle: String) throws -> NSRunningApplication {
    guard !bundle.isEmpty, let app = NSRunningApplication.runningApplications(withBundleIdentifier: bundle).first else { try fail("The approved app is not running") }
    // Do not route model input into terminals, editors, system settings, or this agent.
    let blocked = ["terminal", "iterm", "code", "jetbrains", "systempreferences", "openclerk.runner"]
    guard !blocked.contains(where: { bundle.lowercased().contains($0) }) else { try fail("This application is outside the desktop runner's supported targets") }
    return app
}
func windowFor(_ app: NSRunningApplication) async throws -> SCWindow {
    let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
    let candidates = content.windows.filter { $0.owningApplication?.processID == app.processIdentifier && $0.windowLayer == 0 && $0.frame.width > 100 && $0.frame.height > 100 }
    guard candidates.count == 1, let window = candidates.first else { try fail("Target must have exactly one visible application window. Close extra windows and retry.") }
    return window
}
func focus(_ app: NSRunningApplication) async throws {
    // Activation is requested by the host runner. This bridge only verifies it.
    for _ in 0..<20 {
        if NSWorkspace.shared.frontmostApplication?.processIdentifier == app.processIdentifier { return }
        try await Task.sleep(nanoseconds: 100_000_000)
    }
    try fail("Approved app is not in the foreground")
}
func capture(_ window: SCWindow) async throws -> (Data, Int, Int, String) {
    let configuration = SCStreamConfiguration()
    let width = Int(window.frame.width.rounded()), height = Int(window.frame.height.rounded())
    configuration.width = width; configuration.height = height
    configuration.showsCursor = false
    configuration.ignoreShadowsSingleWindow = true
    let filter = SCContentFilter(desktopIndependentWindow: window)
    let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: configuration)
    let bitmap = NSBitmapImageRep(cgImage: image)
    guard let png = bitmap.representation(using: .png, properties: [:]) else { try fail("Screenshot could not be encoded") }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    try VNImageRequestHandler(cgImage: image).perform([request])
    let text = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
    return (png, image.width, image.height, text)
}
func safeNumber(_ action: [String: Any], _ key: String, _ low: Double, _ high: Double) throws -> Double {
    guard let number = action[key] as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID() else { try fail("Invalid numeric action field: " + key) }
    let value = number.doubleValue
    guard value.isFinite && value >= low && value <= high else { try fail("Action field out of range: " + key) }
    return value
}
func sendInput(_ app: NSRunningApplication, _ window: SCWindow, _ action: [String: Any]) throws {
    guard AXIsProcessTrusted() else { try fail("Accessibility permission is required for mouse and keyboard input") }
    guard NSWorkspace.shared.frontmostApplication?.processIdentifier == app.processIdentifier else { try fail("Foreground changed before input (" + (NSWorkspace.shared.frontmostApplication?.bundleIdentifier ?? "none") + ")") }
    guard let kind = action["kind"] as? String else { try fail("Action kind is missing") }
    let source = CGEventSource(stateID: .hidSystemState)
    if let mouse = CGEvent(source: nil)?.location, mouse.x <= 2 && mouse.y <= 2 { try fail("Emergency stop: pointer is at the upper-left corner") }
    switch kind {
    case "click", "double_click", "scroll":
        let x = try safeNumber(action, "x", 0, window.frame.width - 1), y = try safeNumber(action, "y", 0, window.frame.height - 1)
        let point = CGPoint(x: window.frame.minX + x, y: window.frame.minY + y)
        guard let move = CGEvent(mouseEventSource: source, mouseType: .mouseMoved, mouseCursorPosition: point, mouseButton: .left) else { try fail("Mouse event could not be created") }
        move.post(tap: .cghidEventTap)
        if kind == "scroll" {
            let delta = try safeNumber(action, "delta", -600, 600)
            guard let event = CGEvent(scrollWheelEvent2Source: source, units: .pixel, wheelCount: 1, wheel1: Int32(delta), wheel2: 0, wheel3: 0) else { try fail("Scroll event could not be created") }
            event.post(tap: .cghidEventTap)
        } else {
            for count in 1...(kind == "double_click" ? 2 : 1) {
                guard let down = CGEvent(mouseEventSource: source, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left), let up = CGEvent(mouseEventSource: source, mouseType: .leftMouseUp, mouseCursorPosition: point, mouseButton: .left) else { try fail("Click events could not be created") }
                down.setIntegerValueField(.mouseEventClickState, value: Int64(count)); up.setIntegerValueField(.mouseEventClickState, value: Int64(count))
                down.post(tap: .cghidEventTap); up.post(tap: .cghidEventTap)
            }
        }
    case "type":
        guard let text = action["text"] as? String, !text.isEmpty, text.count <= 1000, !text.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 }) else { try fail("Only printable text is supported") }
        let characters = Array(text.utf16)
        guard let down = CGEvent(keyboardEventSource: source, virtualKey: 0, keyDown: true), let up = CGEvent(keyboardEventSource: source, virtualKey: 0, keyDown: false) else { try fail("Text events could not be created") }
        characters.withUnsafeBufferPointer { pointer in
            down.keyboardSetUnicodeString(stringLength: characters.count, unicodeString: pointer.baseAddress!)
            up.keyboardSetUnicodeString(stringLength: characters.count, unicodeString: pointer.baseAddress!)
        }
        down.post(tap: .cghidEventTap); up.post(tap: .cghidEventTap)
    case "key":
        let keys: [String: CGKeyCode] = ["tab": 48, "enter": 36, "escape": 53, "backspace": 51, "space": 49, "left": 123, "right": 124, "up": 126, "down": 125, "home": 115, "end": 119]
        guard let key = action["key"] as? String, let code = keys[key], let down = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: true), let up = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: false) else { try fail("Key is outside supported navigation keys") }
        down.post(tap: .cghidEventTap); up.post(tap: .cghidEventTap)
    case "wait": break
    default: try fail("Unsupported native action")
    }
}
func run(_ request: [String: Any]) async throws -> [String: Any] {
    let command = request["command"] as? String ?? ""
    if command == "doctor" { return ["ok": true, "platform": "macOS", "screen_recording": CGPreflightScreenCaptureAccess(), "accessibility": AXIsProcessTrusted(), "capture": "ScreenCaptureKit window only", "input": "CoreGraphics mouse and keyboard"] }
    if command == "permissions" {
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
        let access = AXIsProcessTrustedWithOptions(options)
        let capture = CGRequestScreenCaptureAccess()
        return ["ok": true, "accessibility": access, "screen_recording": capture]
    }
    if command == "apps" {
        return ["ok": true, "apps": NSWorkspace.shared.runningApplications.filter { $0.activationPolicy == .regular }.map { ["name": $0.localizedName ?? "App", "bundle_id": $0.bundleIdentifier ?? ""] }]
    }
    guard ["observe", "execute"].contains(command), let bundle = request["bundle_id"] as? String else { try fail("Unknown bridge command") }
    guard CGPreflightScreenCaptureAccess() else { try fail("Screen Recording permission is required. Run openclerk permissions, approve the native bridge in macOS settings, then restart it.") }
    let app = try target(bundle)
    try await focus(app)
    let window = try await windowFor(app)
    let (png, width, height, text) = try await capture(window)
    if command == "observe" { return ["ok": true, "window_id": window.windowID, "process_id": app.processIdentifier, "bounds": boundsJSON(window.frame), "width": width, "height": height, "png": png.base64EncodedString(), "text": text] }
    guard let expectedProcess = request["process_id"] as? Int32, expectedProcess == app.processIdentifier else { try fail("Target process changed. Start a new review.") }
    guard let expectedID = request["window_id"] as? UInt32, expectedID == window.windowID, let expectedBounds = request["bounds"] as? [String: Double], expectedBounds == boundsJSON(window.frame) else { try fail("Window or geometry changed. Capture and review a new action.") }
    let digest = SHA256.hash(data: png).map { String(format: "%02x", $0) }.joined()
    guard let expectedDigest = request["fingerprint_png"] as? String, digest == expectedDigest else { try fail("Screenshot changed since review. Capture and review a new action.") }
    guard let action = request["action"] as? [String: Any] else { try fail("Action is missing") }
    if action["kind"] as? String == "wait" { let seconds = try safeNumber(action, "seconds", 0, 5); try await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000)) }
    else { try sendInput(app, window, action); try await Task.sleep(nanoseconds: 350_000_000) }
    return ["ok": true, "input_posted": true]
}
let application = NSApplication.shared
application.setActivationPolicy(.prohibited)
func handle(_ data: Data, exitAfter: Bool) async {
    do {
        guard let request = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { try fail("Request must be a JSON object") }
        emit(try await run(request))
    } catch {
        emit(["ok": false, "error": (error as? BridgeError)?.message ?? String(describing: error)])
    }
    if exitAfter { exit(0) }
}
if CommandLine.arguments.contains("--session") {
    DispatchQueue.global().async {
        while let line = readLine() {
            let data = Data(line.utf8)
            Task { @MainActor in await handle(data, exitAfter: false) }
        }
        Task { @MainActor in exit(0) }
    }
} else {
    let input = FileHandle.standardInput.readDataToEndOfFile()
    Task { @MainActor in await handle(input, exitAfter: true) }
}
application.run()
