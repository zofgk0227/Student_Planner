import SwiftUI

@main
struct StudentPlannerApp: App {
    @StateObject private var store = TaskStore()

    var body: some Scene {
        WindowGroup {
            PlannerTabView()
                .environmentObject(store)
                .tint(PlannerPalette.violet)
        }
    }
}
