import SwiftUI

enum PlannerPalette {
    static let ink = Color(hex: 0x20203A)
    static let muted = Color(hex: 0x85859D)
    static let canvas = Color(hex: 0xF5F4FB)
    static let violet = Color(hex: 0x6C55E8)
    static let pink = Color(hex: 0xF16B9A)
    static let orange = Color(hex: 0xFFAA63)
    static let teal = Color(hex: 0x49BDB1)
    static let blue = Color(hex: 0x6B9FF2)
    static let card = Color.white
    static let line = Color(hex: 0xECEAF4)
}

private extension Color {
    init(hex: UInt) {
        self.init(
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255
        )
    }
}

private enum PlannerTab: String, CaseIterable {
    case today = "Today"
    case tasks = "Tasks"
    case schedule = "Schedule"
    case progress = "Progress"

    var symbol: String {
        switch self {
        case .today: "sparkles"
        case .tasks: "checklist"
        case .schedule: "calendar"
        case .progress: "chart.bar.fill"
        }
    }
}

struct PlannerTabView: View {
    @EnvironmentObject private var store: TaskStore
    @State private var selectedTab: PlannerTab = .today
    @State private var showingStorageError = false

    var body: some View {
        TabView(selection: $selectedTab) {
            TodayView()
                .tabItem { Label(PlannerTab.today.rawValue, systemImage: PlannerTab.today.symbol) }
                .tag(PlannerTab.today)
            TaskListView()
                .tabItem { Label(PlannerTab.tasks.rawValue, systemImage: PlannerTab.tasks.symbol) }
                .tag(PlannerTab.tasks)
            ScheduleView()
                .tabItem { Label(PlannerTab.schedule.rawValue, systemImage: PlannerTab.schedule.symbol) }
                .tag(PlannerTab.schedule)
            ProgressOverview()
                .tabItem { Label(PlannerTab.progress.rawValue, systemImage: PlannerTab.progress.symbol) }
                .tag(PlannerTab.progress)
        }
        .background(PlannerPalette.canvas.ignoresSafeArea())
        .alert("Storage issue", isPresented: $showingStorageError) {
            Button("OK", role: .cancel) { store.storageError = nil }
        } message: {
            Text(store.storageError ?? "")
        }
        .onChange(of: store.storageError) { message in
            showingStorageError = message != nil
        }
        .onAppear {
            showingStorageError = store.storageError != nil
        }
    }
}

private struct ScreenScaffold<Content: View>: View {
    let title: String
    var subtitle: String? = nil
    @ViewBuilder let content: Content

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    VStack(alignment: .leading, spacing: 5) {
                        Text(title)
                            .font(.system(size: 32, weight: .bold, design: .rounded))
                            .foregroundStyle(PlannerPalette.ink)
                        if let subtitle {
                            Text(subtitle)
                                .font(.subheadline)
                                .foregroundStyle(PlannerPalette.muted)
                        }
                    }
                    content
                }
                .padding(.horizontal, 20)
                .padding(.top, 16)
                .padding(.bottom, 30)
            }
            .background(PlannerPalette.canvas.ignoresSafeArea())
            .toolbar(.hidden, for: .navigationBar)
        }
    }
}

private struct TodayView: View {
    @EnvironmentObject private var store: TaskStore
    @State private var showingAddTask = false
    @State private var dailyBudget = 120
    private var plan: [(task: PlannerTask, minutes: Int)] { store.plan(budget: dailyBudget) }
    private var dueCount: Int { store.tasks.filter { !$0.isComplete }.count }

    var body: some View {
        ScreenScaffold(title: greeting, subtitle: Date.now.formatted(.dateTime.weekday(.wide).month(.wide).day())) {
            VStack(alignment: .leading, spacing: 18) {
                heroCard
                HStack(spacing: 12) {
                    MetricCard(value: "\(dueCount)", label: "To do", tint: PlannerPalette.pink, symbol: "checkmark.circle.fill")
                    MetricCard(value: "\(plan.reduce(0) { $0 + $1.minutes })m", label: "Study plan", tint: PlannerPalette.teal, symbol: "timer")
                    MetricCard(value: "\(store.tasks.filter(\.isComplete).count)", label: "Done", tint: PlannerPalette.orange, symbol: "star.fill")
                }
                HStack {
                    Text("Your focus plan")
                        .font(.title3.bold())
                        .foregroundStyle(PlannerPalette.ink)
                    Spacer()
                }
                HStack(spacing: 10) {
                    Image(systemName: "timer")
                        .foregroundStyle(PlannerPalette.violet)
                    Text("Study time")
                        .font(.subheadline.weight(.medium))
                        .foregroundStyle(PlannerPalette.ink)
                    Spacer()
                    Picker("Daily study time", selection: $dailyBudget) {
                        ForEach([30, 45, 60, 90, 120, 150, 180, 240, 300], id: \.self) { minutes in
                            Text("\(minutes) min").tag(minutes)
                        }
                    }
                    .labelsHidden()
                    .tint(PlannerPalette.violet)
                }
                .padding(.horizontal, 13)
                .padding(.vertical, 8)
                .plannerCard()
                if plan.isEmpty {
                    EmptyState(
                        symbol: "sun.max.fill",
                        title: "A clear mind starts here",
                        message: "Add a task and we’ll help shape your study plan."
                    )
                } else {
                    VStack(spacing: 10) {
                        ForEach(plan, id: \.task.id) { item in
                            PlanRow(task: item.task, minutes: item.minutes)
                        }
                    }
                }
                if let nextTask = store.tasks.filter({ !$0.isComplete }).sorted(by: { $0.dueDate < $1.dueDate }).first {
                    VStack(alignment: .leading, spacing: 10) {
                        SectionHeading(title: "Coming up", eyebrow: "NEXT DEADLINE", tint: PlannerPalette.orange)
                        HStack(spacing: 12) {
                            RoundedRectangle(cornerRadius: 2)
                                .fill(PlannerPalette.orange)
                                .frame(width: 4)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(nextTask.name).font(.headline).foregroundStyle(PlannerPalette.ink)
                                Text(nextTask.subject).font(.subheadline).foregroundStyle(PlannerPalette.muted)
                            }
                            Spacer(minLength: 4)
                            Text(nextTask.dueDate.formatted(.dateTime.month(.abbreviated).day()))
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(PlannerPalette.ink)
                        }
                        .padding(14)
                        .plannerCard()
                    }
                }
            }
        }
        .overlay(alignment: .topTrailing) {
            Button { showingAddTask = true } label: {
                Image(systemName: "plus")
                    .font(.headline.weight(.bold))
                    .foregroundStyle(.white)
                    .frame(width: 44, height: 44)
                    .background(PlannerPalette.violet, in: Circle())
                    .shadow(color: PlannerPalette.violet.opacity(0.25), radius: 10, y: 5)
            }
            .padding(.trailing, 20)
            .padding(.top, 18)
            .accessibilityLabel("Add task")
        }
        .sheet(isPresented: $showingAddTask) {
            TaskEditor(existingTask: nil) { store.add($0) }
        }
    }

    private var greeting: String {
        let hour = Calendar.current.component(.hour, from: .now)
        return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening"
    }

    private var heroCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 8) {
                    Text("MAKE TODAY\nCOUNT")
                        .font(.caption.weight(.heavy))
                        .tracking(1.5)
                        .foregroundStyle(.white.opacity(0.78))
                    Text("Small steps.\nBig progress.")
                        .font(.system(size: 27, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                }
                Spacer()
                Image(systemName: "sparkles")
                    .font(.system(size: 38, weight: .medium))
                    .foregroundStyle(.white.opacity(0.9))
                    .frame(width: 74, height: 74)
                    .background(.white.opacity(0.16), in: Circle())
            }
            HStack(spacing: 8) {
                Image(systemName: "bolt.fill")
                Text("One thing at a time")
            }
            .font(.caption.weight(.semibold))
            .foregroundStyle(.white.opacity(0.92))
        }
        .padding(22)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            LinearGradient(
                colors: [PlannerPalette.violet, Color(hex: 0x9C61E8), PlannerPalette.pink],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 28, style: .continuous)
        )
    }
}

private struct TaskListView: View {
    @EnvironmentObject private var store: TaskStore
    @State private var filter: TaskFilter = .upcoming
    @State private var searchText = ""
    @State private var showingAddTask = false
    @State private var editingTask: PlannerTask?

    private var visibleTasks: [PlannerTask] {
        store.tasks
            .filter { filter.matches($0) }
            .filter { searchText.isEmpty || $0.name.localizedCaseInsensitiveContains(searchText) || $0.subject.localizedCaseInsensitiveContains(searchText) }
            .sorted { $0.dueDate < $1.dueDate }
    }

    var body: some View {
        ScreenScaffold(title: "My tasks", subtitle: "A little progress adds up.") {
            Picker("Task filter", selection: $filter) {
                ForEach(TaskFilter.allCases) { option in
                    Text(option.title).tag(option)
                }
            }
            .pickerStyle(.segmented)

            HStack(spacing: 10) {
                Image(systemName: "magnifyingglass").foregroundStyle(PlannerPalette.muted)
                TextField("Find a task or subject", text: $searchText)
                    .autocorrectionDisabled()
            }
            .padding(13)
            .background(PlannerPalette.card, in: RoundedRectangle(cornerRadius: 16, style: .continuous))

            if visibleTasks.isEmpty {
                EmptyState(
                    symbol: filter == .completed ? "party.popper.fill" : "checkmark.circle.fill",
                    title: filter == .completed ? "No finished tasks yet" : "Nothing on your list",
                    message: filter == .overdue ? "You’re all caught up on deadlines." : "Tap + to add your first task."
                )
            } else {
                LazyVStack(spacing: 11) {
                    ForEach(visibleTasks) { task in
                        TaskCard(
                            task: task,
                            onToggle: { store.toggleComplete(task) },
                            onLog: { store.log(minutes: 15, for: task) },
                            onEdit: { editingTask = task }
                        )
                        .contextMenu {
                            Button(task.isComplete ? "Mark as not done" : "Mark as done", systemImage: task.isComplete ? "arrow.uturn.backward" : "checkmark") {
                                store.toggleComplete(task)
                            }
                            Button("Edit task", systemImage: "pencil") { editingTask = task }
                            Button("Delete task", systemImage: "trash", role: .destructive) { store.delete(task) }
                        }
                    }
                }
            }
        }
        .overlay(alignment: .topTrailing) {
            Button { showingAddTask = true } label: {
                Image(systemName: "plus")
                    .font(.headline.weight(.bold))
                    .foregroundStyle(.white)
                    .frame(width: 44, height: 44)
                    .background(PlannerPalette.violet, in: Circle())
            }
            .padding(.trailing, 20)
            .padding(.top, 18)
            .accessibilityLabel("Add task")
        }
        .sheet(isPresented: $showingAddTask) {
            TaskEditor(existingTask: nil) { store.add($0) }
        }
        .sheet(item: $editingTask) { task in
            TaskEditor(existingTask: task) { store.update($0) }
        }
    }
}

private enum TaskFilter: String, CaseIterable, Identifiable {
    case upcoming
    case overdue
    case completed

    var id: String { rawValue }
    var title: String {
        switch self {
        case .upcoming: "To do"
        case .overdue: "Overdue"
        case .completed: "Done"
        }
    }

    func matches(_ task: PlannerTask) -> Bool {
        switch self {
        case .upcoming: !task.isComplete && !task.isOverdue
        case .overdue: task.isOverdue
        case .completed: task.isComplete
        }
    }
}

private struct ScheduleView: View {
    @EnvironmentObject private var store: TaskStore
    @State private var selectedDate = Date.now

    private var dayTasks: [PlannerTask] {
        store.tasks
            .filter { Calendar.current.isDate($0.dueDate, inSameDayAs: selectedDate) }
            .sorted { $0.priority > $1.priority }
    }

    var body: some View {
        ScreenScaffold(title: "Schedule", subtitle: "See what’s coming up.") {
            DatePicker("Choose a day", selection: $selectedDate, displayedComponents: .date)
                .datePickerStyle(.graphical)
                .tint(PlannerPalette.violet)
                .padding(.horizontal, 8)
                .padding(.vertical, 12)
                .plannerCard()

            SectionHeading(
                title: selectedDate.formatted(.dateTime.weekday(.wide).month(.wide).day()),
                eyebrow: "YOUR DAY",
                tint: PlannerPalette.blue
            )
            if dayTasks.isEmpty {
                EmptyState(symbol: "calendar", title: "A little breathing room", message: "No deadlines on this day.")
            } else {
                VStack(spacing: 10) {
                    ForEach(dayTasks) { task in
                        TaskCard(
                            task: task,
                            onToggle: { store.toggleComplete(task) },
                            onLog: { store.log(minutes: 15, for: task) }
                        )
                    }
                }
            }
        }
    }
}

private struct ProgressOverview: View {
    @EnvironmentObject private var store: TaskStore
    @State private var isImporting = false
    @State private var isExporting = false
    @State private var exportDocument = PlannerJSONDocument(data: Data("[]".utf8))
    @State private var transferAlert: TransferAlert?

    private var total: Int { store.tasks.count }
    private var completed: Int { store.tasks.filter(\.isComplete).count }
    private var minutes: Int { store.tasks.reduce(0) { $0 + $1.loggedMinutes } }

    var body: some View {
        ScreenScaffold(title: "Your progress", subtitle: "Celebrate every step forward.") {
            VStack(alignment: .leading, spacing: 18) {
                HStack(spacing: 14) {
                    ZStack {
                        Circle().stroke(PlannerPalette.violet.opacity(0.12), lineWidth: 12)
                        Circle()
                            .trim(from: 0, to: total == 0 ? 0 : Double(completed) / Double(total))
                            .stroke(
                                AngularGradient(colors: [PlannerPalette.violet, PlannerPalette.pink, PlannerPalette.orange], center: .center),
                                style: StrokeStyle(lineWidth: 12, lineCap: .round)
                            )
                            .rotationEffect(.degrees(-90))
                        VStack(spacing: 1) {
                            Text(total == 0 ? "0%" : "\(Int(Double(completed) / Double(total) * 100))%")
                                .font(.system(size: 25, weight: .bold, design: .rounded))
                                .foregroundStyle(PlannerPalette.ink)
                            Text("done").font(.caption2).foregroundStyle(PlannerPalette.muted)
                        }
                    }
                    .frame(width: 112, height: 112)
                    VStack(alignment: .leading, spacing: 5) {
                        Text(total == 0 ? "Your journey starts here" : "\(completed) of \(total) tasks")
                            .font(.headline)
                            .foregroundStyle(PlannerPalette.ink)
                        Text(total == 0 ? "Add a task to start tracking your progress." : "Keep the momentum going.")
                            .font(.subheadline)
                            .foregroundStyle(PlannerPalette.muted)
                    }
                }
                .padding(18)
                .plannerCard()

                HStack(spacing: 12) {
                    MetricCard(value: "\(completed)", label: "Completed", tint: PlannerPalette.teal, symbol: "checkmark.seal.fill")
                    MetricCard(value: "\(minutes / 60)h \(minutes % 60)m", label: "Time studied", tint: PlannerPalette.pink, symbol: "clock.fill")
                }

                SectionHeading(title: "Subject snapshot", eyebrow: "BY SUBJECT", tint: PlannerPalette.orange)
                let subjects = Dictionary(grouping: store.tasks, by: \.subject)
                if subjects.isEmpty {
                    EmptyState(symbol: "books.vertical.fill", title: "Your subjects will show up here", message: "Add tasks to see your study mix.")
                } else {
                    VStack(spacing: 16) {
                        ForEach(subjects.keys.sorted(), id: \.self) { subject in
                            let subjectTasks = subjects[subject] ?? []
                            let doneCount = subjectTasks.filter(\.isComplete).count
                            VStack(alignment: .leading, spacing: 7) {
                                HStack {
                                    Text(subject).font(.subheadline.weight(.semibold)).foregroundStyle(PlannerPalette.ink)
                                    Spacer()
                                    Text("\(doneCount)/\(subjectTasks.count)")
                                        .font(.caption.weight(.medium))
                                        .foregroundStyle(PlannerPalette.muted)
                                }
                                ProgressView(value: subjectTasks.isEmpty ? 0 : Double(doneCount) / Double(subjectTasks.count))
                                    .tint([PlannerPalette.violet, PlannerPalette.pink, PlannerPalette.teal, PlannerPalette.orange][subject.count % 4])
                            }
                        }
                    }
                    .padding(18)
                    .plannerCard()
                }

                SectionHeading(title: "Move your tasks", eyebrow: "DATA", tint: PlannerPalette.blue)
                VStack(alignment: .leading, spacing: 12) {
                    Text("Bring in a task list from the desktop planner, or save a JSON copy for later.")
                        .font(.subheadline)
                        .foregroundStyle(PlannerPalette.muted)
                    HStack(spacing: 10) {
                        Button {
                            isImporting = true
                        } label: {
                            Label("Import JSON", systemImage: "square.and.arrow.down")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)

                        Button(action: prepareExport) {
                            Label("Export", systemImage: "square.and.arrow.up")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                    }
                    .font(.subheadline.weight(.semibold))
                }
                .padding(16)
                .plannerCard()
            }
        }
        .fileImporter(
            isPresented: $isImporting,
            allowedContentTypes: [.json],
            allowsMultipleSelection: false,
            onCompletion: importTasks
        )
        .fileExporter(
            isPresented: $isExporting,
            document: exportDocument,
            contentType: .json,
            defaultFilename: "student_planner_tasks",
            onCompletion: exportFinished
        )
        .alert(item: $transferAlert) { alert in
            Alert(
                title: Text(alert.title),
                message: Text(alert.message),
                dismissButton: .default(Text("OK"))
            )
        }
    }

    private func prepareExport() {
        do {
            exportDocument = PlannerJSONDocument(data: try store.exportLegacyJSON())
            isExporting = true
        } catch {
            transferAlert = TransferAlert(title: "Export failed", message: error.localizedDescription)
        }
    }

    private func importTasks(_ result: Result<[URL], Error>) {
        do {
            guard let url = try result.get().first else { return }
            let didStartAccessing = url.startAccessingSecurityScopedResource()
            defer {
                if didStartAccessing {
                    url.stopAccessingSecurityScopedResource()
                }
            }
            let count = try store.importLegacyJSON(Data(contentsOf: url))
            transferAlert = TransferAlert(
                title: "Import complete",
                message: count == 0
                    ? "No new tasks were found. Existing tasks were kept."
                    : "Added \(count) task\(count == 1 ? "" : "s"). Existing tasks were kept."
            )
        } catch {
            if (error as NSError).code != NSUserCancelledError {
                transferAlert = TransferAlert(title: "Import failed", message: error.localizedDescription)
            }
        }
    }

    private func exportFinished(_ result: Result<URL, Error>) {
        if case .failure(let error) = result {
            if (error as NSError).code != NSUserCancelledError {
                transferAlert = TransferAlert(title: "Export failed", message: error.localizedDescription)
            }
        }
    }
}

private struct TransferAlert: Identifiable {
    let id = UUID()
    let title: String
    let message: String
}

private struct TaskEditor: View {
    @Environment(\.dismiss) private var dismiss
    let existingTask: PlannerTask?
    let onSave: (PlannerTask) -> Void

    @State private var name: String
    @State private var subject: String
    @State private var dueDate: Date
    @State private var estimatedMinutes: Int
    @State private var dailyTarget: Int
    @State private var priority: Int

    init(existingTask: PlannerTask?, onSave: @escaping (PlannerTask) -> Void) {
        self.existingTask = existingTask
        self.onSave = onSave
        _name = State(initialValue: existingTask?.name ?? "")
        _subject = State(initialValue: existingTask?.subject ?? "")
        _dueDate = State(initialValue: existingTask?.dueDate ?? Calendar.current.date(byAdding: .day, value: 1, to: .now) ?? .now)
        _estimatedMinutes = State(initialValue: existingTask?.estimatedMinutes ?? 60)
        _dailyTarget = State(initialValue: existingTask?.dailyTargetMinutes ?? 30)
        _priority = State(initialValue: existingTask?.priority ?? 5)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("THE TASK") {
                    TextField("Task name", text: $name)
                    TextField("Subject", text: $subject)
                }
                Section("WHEN") {
                    DatePicker("Due date", selection: $dueDate, displayedComponents: .date)
                }
                Section {
                    Stepper("Estimated time · \(estimatedMinutes) min", value: $estimatedMinutes, in: 15...600, step: 15)
                    Stepper("Daily target · \(dailyTarget) min", value: $dailyTarget, in: 15...240, step: 15)
                    Picker("Priority", selection: $priority) {
                        ForEach(1...10, id: \.self) { value in
                            Text("\(value) / 10").tag(value)
                        }
                    }
                    .tint(PlannerPalette.violet)
                } header: {
                    Text("STUDY PLAN")
                }
            }
            .scrollContentBackground(.hidden)
            .background(PlannerPalette.canvas)
            .navigationTitle(existingTask == nil ? "New task" : "Edit task")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { save() }
                        .fontWeight(.semibold)
                        .disabled(name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
                                  subject.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
        .tint(PlannerPalette.violet)
    }

    private func save() {
        let cleanedName = name.trimmingCharacters(in: .whitespacesAndNewlines)
        let cleanedSubject = subject.trimmingCharacters(in: .whitespacesAndNewlines)
        var task = existingTask ?? PlannerTask(
            name: cleanedName,
            subject: cleanedSubject,
            estimatedMinutes: estimatedMinutes,
            dailyTargetMinutes: dailyTarget,
            loggedMinutes: 0,
            priority: priority,
            dueDate: dueDate,
            isComplete: false
        )
        task.name = cleanedName
        task.subject = cleanedSubject
        task.estimatedMinutes = estimatedMinutes
        task.dailyTargetMinutes = dailyTarget
        task.priority = priority
        task.dueDate = dueDate
        task.loggedMinutes = min(task.loggedMinutes, estimatedMinutes)
        onSave(task)
        dismiss()
    }
}

private struct TaskCard: View {
    let task: PlannerTask
    let onToggle: () -> Void
    var onLog: (() -> Void)? = nil
    var onEdit: (() -> Void)? = nil

    var body: some View {
        HStack(spacing: 12) {
            Button(action: onToggle) {
                Image(systemName: task.isComplete ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 24))
                    .foregroundStyle(task.isComplete ? PlannerPalette.teal : PlannerPalette.violet.opacity(0.8))
            }
            .buttonStyle(.plain)
            .accessibilityLabel(task.isComplete ? "Mark task incomplete" : "Complete task")

            VStack(alignment: .leading, spacing: 6) {
                Text(task.name)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(task.isComplete ? PlannerPalette.muted : PlannerPalette.ink)
                    .strikethrough(task.isComplete)
                    .lineLimit(1)
                HStack(spacing: 7) {
                    Text(task.subject)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(PlannerPalette.violet)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(PlannerPalette.violet.opacity(0.09), in: Capsule())
                    Label("\(task.remainingMinutes) min", systemImage: "clock")
                        .font(.caption2)
                        .foregroundStyle(PlannerPalette.muted)
                }
            }
            Spacer(minLength: 3)
            VStack(alignment: .trailing, spacing: 4) {
                Text(task.dueDate.formatted(.dateTime.month(.abbreviated).day()))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(task.isOverdue ? PlannerPalette.pink : PlannerPalette.ink)
                Text("P\(task.priority)")
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(PlannerPalette.orange)
            }
            if !task.isComplete, let onLog {
                Button(action: onLog) {
                    Label("15m", systemImage: "clock.badge.plus")
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(PlannerPalette.teal)
                        .padding(7)
                        .background(PlannerPalette.teal.opacity(0.1), in: Capsule())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Log 15 study minutes for \(task.name)")
            }
            if let onEdit {
                Button(action: onEdit) {
                    Image(systemName: "pencil")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(PlannerPalette.violet)
                        .padding(9)
                        .background(PlannerPalette.violet.opacity(0.09), in: Circle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Edit \(task.name)")
            }
        }
        .padding(14)
        .plannerCard()
    }
}

private struct PlanRow: View {
    let task: PlannerTask
    let minutes: Int

    var body: some View {
        HStack(spacing: 12) {
            Text(task.dueDate.formatted(.dateTime.day()))
                .font(.headline.weight(.bold))
                .foregroundStyle(.white)
                .frame(width: 44, height: 44)
                .background(PlannerPalette.violet, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
            VStack(alignment: .leading, spacing: 4) {
                Text(task.name).font(.subheadline.weight(.semibold)).foregroundStyle(PlannerPalette.ink).lineLimit(1)
                Text(task.subject).font(.caption).foregroundStyle(PlannerPalette.muted)
            }
            Spacer(minLength: 2)
            Text("\(minutes)m")
                .font(.caption.weight(.bold))
                .foregroundStyle(PlannerPalette.teal)
                .padding(.horizontal, 10)
                .padding(.vertical, 7)
                .background(PlannerPalette.teal.opacity(0.1), in: Capsule())
        }
        .padding(12)
        .plannerCard()
    }
}

private struct MetricCard: View {
    let value: String
    let label: String
    let tint: Color
    let symbol: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Image(systemName: symbol)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(tint)
                .frame(width: 34, height: 34)
                .background(tint.opacity(0.13), in: RoundedRectangle(cornerRadius: 11, style: .continuous))
            Text(value)
                .font(.system(size: 19, weight: .bold, design: .rounded))
                .foregroundStyle(PlannerPalette.ink)
                .lineLimit(1)
                .minimumScaleFactor(0.75)
            Text(label)
                .font(.caption)
                .foregroundStyle(PlannerPalette.muted)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(13)
        .plannerCard()
    }
}

private struct SectionHeading: View {
    let title: String
    let eyebrow: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(eyebrow)
                .font(.caption2.weight(.heavy))
                .tracking(1.1)
                .foregroundStyle(tint)
            Text(title)
                .font(.title3.bold())
                .foregroundStyle(PlannerPalette.ink)
        }
    }
}

private struct EmptyState: View {
    let symbol: String
    let title: String
    let message: String

    var body: some View {
        VStack(spacing: 9) {
            Image(systemName: symbol)
                .font(.system(size: 27, weight: .medium))
                .foregroundStyle(PlannerPalette.violet)
                .frame(width: 58, height: 58)
                .background(PlannerPalette.violet.opacity(0.1), in: Circle())
            Text(title).font(.headline).foregroundStyle(PlannerPalette.ink)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(PlannerPalette.muted)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(24)
        .plannerCard()
    }
}

private extension View {
    func plannerCard() -> some View {
        background(PlannerPalette.card, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(PlannerPalette.line.opacity(0.8), lineWidth: 1)
            }
    }
}
