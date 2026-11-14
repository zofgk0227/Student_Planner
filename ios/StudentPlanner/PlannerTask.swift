import Foundation
import Combine

enum TaskImportError: LocalizedError {
    case invalidDate(String)
    case invalidTask(String)

    var errorDescription: String? {
        switch self {
        case .invalidDate(let value):
            "The due date “\(value)” is not in YYYY-MM-DD format."
        case .invalidTask(let name):
            "“\(name)” has invalid task details. Check its name, subject, time, and priority."
        }
    }
}

struct LegacyPlannerTask: Codable {
    var taskName: String
    var taskSubject: String
    var estimatedTime: Int
    var dailyWorkTarget: Int?
    var timeSpent: Int?
    var priority: Int?
    var dueDate: String
    var status: String?

    enum CodingKeys: String, CodingKey {
        case taskName
        case taskSubject
        case estimatedTime
        case dailyWorkTarget
        case timeSpent
        case priority
        case dueDate
        case status
    }
}

struct PlannerTask: Identifiable, Codable, Equatable {
    var id = UUID()
    var name: String
    var subject: String
    var estimatedMinutes: Int
    var dailyTargetMinutes: Int
    var loggedMinutes: Int
    var priority: Int
    var dueDate: Date
    var isComplete: Bool

    var remainingMinutes: Int {
        isComplete ? 0 : max(0, estimatedMinutes - loggedMinutes)
    }

    var isOverdue: Bool {
        !isComplete && Calendar.current.startOfDay(for: dueDate) < Calendar.current.startOfDay(for: .now)
    }
}

@MainActor
final class TaskStore: ObservableObject {
    @Published private(set) var tasks: [PlannerTask] {
        didSet { save() }
    }
    @Published var storageError: String?

    private let storageKey = "student-planner.tasks.v1"

    init() {
        var loadedTasks: [PlannerTask] = []
        var loadError: String?
        if let data = UserDefaults.standard.data(forKey: storageKey) {
            do {
                let decoder = JSONDecoder()
                decoder.dateDecodingStrategy = .iso8601
                loadedTasks = try decoder.decode([PlannerTask].self, from: data)
            } catch {
                loadError = "Saved tasks could not be loaded: \(error.localizedDescription)"
            }
        }
        tasks = loadedTasks
        storageError = loadError
    }

    func add(_ task: PlannerTask) {
        tasks.append(task)
    }

    func update(_ task: PlannerTask) {
        guard let index = tasks.firstIndex(where: { $0.id == task.id }) else { return }
        tasks[index] = task
    }

    func delete(_ task: PlannerTask) {
        tasks.removeAll { $0.id == task.id }
    }

    func toggleComplete(_ task: PlannerTask) {
        guard let index = tasks.firstIndex(where: { $0.id == task.id }) else { return }
        tasks[index].isComplete.toggle()
    }

    func log(minutes: Int, for task: PlannerTask) {
        guard minutes > 0 else { return }
        guard let index = tasks.firstIndex(where: { $0.id == task.id }) else { return }
        tasks[index].loggedMinutes = min(tasks[index].estimatedMinutes, tasks[index].loggedMinutes + minutes)
        if tasks[index].loggedMinutes >= tasks[index].estimatedMinutes {
            tasks[index].isComplete = true
        }
    }

    @discardableResult
    func importLegacyJSON(_ data: Data) throws -> Int {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let imported = try decoder.decode([LegacyPlannerTask].self, from: data)
        let dateFormatter = DateFormatter()
        dateFormatter.calendar = Calendar(identifier: .gregorian)
        dateFormatter.locale = Locale(identifier: "en_US_POSIX")
        dateFormatter.timeZone = .current
        dateFormatter.dateFormat = "yyyy-MM-dd"
        dateFormatter.isLenient = false

        var knownTasks = Set(tasks.map(Self.importKey))
        var newTasks: [PlannerTask] = []
        for item in imported {
            let name = item.taskName.trimmingCharacters(in: .whitespacesAndNewlines)
            let subject = item.taskSubject.trimmingCharacters(in: .whitespacesAndNewlines)
            guard
                !name.isEmpty,
                !subject.isEmpty,
                item.estimatedTime > 0,
                (item.priority ?? 5) >= 1,
                (item.priority ?? 5) <= 10,
                item.dueDate.range(of: #"^\d{4}-\d{2}-\d{2}$"#, options: .regularExpression) != nil,
                let dueDate = dateFormatter.date(from: item.dueDate)
            else {
                if dateFormatter.date(from: item.dueDate) == nil {
                    throw TaskImportError.invalidDate(item.dueDate)
                }
                throw TaskImportError.invalidTask(name.isEmpty ? item.taskName : name)
            }

            let estimatedMinutes = item.estimatedTime
            let loggedMinutes = min(max(0, item.timeSpent ?? 0), estimatedMinutes)
            let task = PlannerTask(
                name: name,
                subject: subject,
                estimatedMinutes: estimatedMinutes,
                dailyTargetMinutes: max(1, item.dailyWorkTarget ?? 30),
                loggedMinutes: loggedMinutes,
                priority: item.priority ?? 5,
                dueDate: dueDate,
                isComplete: item.status == "done" || loggedMinutes >= estimatedMinutes
            )
            let key = Self.importKey(task)
            if knownTasks.insert(key).inserted {
                newTasks.append(task)
            }
        }
        tasks.append(contentsOf: newTasks)
        return newTasks.count
    }

    func exportLegacyJSON() throws -> Data {
        let exported = tasks.map {
            LegacyPlannerTask(
                taskName: $0.name,
                taskSubject: $0.subject,
                estimatedTime: $0.estimatedMinutes,
                dailyWorkTarget: $0.dailyTargetMinutes,
                timeSpent: $0.loggedMinutes,
                priority: $0.priority,
                dueDate: Self.legacyDateFormatter.string(from: $0.dueDate),
                status: $0.isComplete ? "done" : "due"
            )
        }
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(exported)
    }

    func plan(budget: Int = 120) -> [(task: PlannerTask, minutes: Int)] {
        var minutesLeft = max(0, budget)
        let ordered = tasks
            .filter { !$0.isComplete && $0.remainingMinutes > 0 }
            .sorted {
                let firstDue = Calendar.current.startOfDay(for: $0.dueDate)
                let secondDue = Calendar.current.startOfDay(for: $1.dueDate)
                if firstDue != secondDue { return firstDue < secondDue }
                return $0.priority > $1.priority
            }

        return ordered.compactMap { task in
            guard minutesLeft > 0 else { return nil }
            let target = min(max(15, task.dailyTargetMinutes), task.remainingMinutes)
            let amount = min(target, minutesLeft)
            minutesLeft -= amount
            return (task: task, minutes: amount)
        }
        .filter { $0.minutes > 0 }
    }

    private func save() {
        do {
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            UserDefaults.standard.set(try encoder.encode(tasks), forKey: storageKey)
            storageError = nil
        } catch {
            storageError = "Your changes could not be saved: \(error.localizedDescription)"
        }
    }

    private static let legacyDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = .current
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    private static func importKey(_ task: PlannerTask) -> String {
        [
            task.name.lowercased(),
            task.subject.lowercased(),
            legacyDateFormatter.string(from: task.dueDate),
            String(task.estimatedMinutes),
            String(task.priority),
        ].joined(separator: "|")
    }
}
