import React, { useState } from 'react';
import { Calendar, Clock, Plus, Trash2, Settings, Send, RefreshCw } from 'lucide-react';

export default function TaskPlanner() {
  const [tasks, setTasks] = useState([]);
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('tasks');

  const [currentTask, setCurrentTask] = useState({
    name: '',
    subject: '',
    estimatedHours: '',
    deadline: '',
    priority: 'medium'
  });

  const [preferences, setPreferences] = useState({
    studyWindows: '',
    maxDailyHours: '',
    breakPattern: '',
    additionalNotes: ''
  });

  const addTask = () => {
    if (currentTask.name && currentTask.estimatedHours && currentTask.deadline) {
      setTasks([...tasks, { ...currentTask, id: Date.now() }]);
      setCurrentTask({
        name: '',
        subject: '',
        estimatedHours: '',
        deadline: '',
        priority: 'medium'
      });
    }
  };

  const removeTask = (id) => {
    setTasks(tasks.filter(t => t.id !== id));
  };

  const generateSchedule = async () => {
    setLoading(true);

    // Simulate API call
    setTimeout(() => {
      const mockSchedule = {
        events: tasks.flatMap((task, idx) => {
          const sessions = Math.ceil(task.estimatedHours / 2);
          return Array.from({ length: sessions }, (_, i) => ({
            taskName: task.name,
            date: new Date(new Date(task.deadline).getTime() - (sessions - i) * 86400000).toLocaleDateString(),
            startTime: '14:00',
            duration: Math.min(2, task.estimatedHours - i * 2),
            type: task.subject
          }));
        }),
        summary: {
          totalTasks: tasks.length,
          totalHours: tasks.reduce((sum, t) => sum + parseFloat(t.estimatedHours), 0),
          daysUsed: 5
        }
      };

      setSchedule(mockSchedule);
      setLoading(false);
      setActiveTab('schedule');
    }, 1500);
  };

  const resetAll = () => {
    setTasks([]);
    setSchedule(null);
    setActiveTab('tasks');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-indigo-600 p-3 rounded-lg">
                <Calendar className="text-white" size={28} />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-800">AI Task Planner</h1>
                <p className="text-gray-600">Smart scheduling powered by LLM</p>
              </div>
            </div>
            <button
              onClick={resetAll}
              className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
            >
              <RefreshCw size={18} />
              Reset
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white rounded-lg shadow-lg mb-6">
          <div className="flex border-b">
            <button
              onClick={() => setActiveTab('tasks')}
              className={`flex-1 px-6 py-4 font-semibold transition ${activeTab === 'tasks'
                ? 'text-indigo-600 border-b-2 border-indigo-600'
                : 'text-gray-600 hover:text-gray-800'
                }`}
            >
              Tasks ({tasks.length})
            </button>
            <button
              onClick={() => setActiveTab('preferences')}
              className={`flex-1 px-6 py-4 font-semibold transition ${activeTab === 'preferences'
                ? 'text-indigo-600 border-b-2 border-indigo-600'
                : 'text-gray-600 hover:text-gray-800'
                }`}
            >
              Preferences
            </button>
            <button
              onClick={() => setActiveTab('schedule')}
              className={`flex-1 px-6 py-4 font-semibold transition ${activeTab === 'schedule'
                ? 'text-indigo-600 border-b-2 border-indigo-600'
                : 'text-gray-600 hover:text-gray-800'
                }`}
            >
              Schedule
            </button>
          </div>

          <div className="p-6">
            {/* Tasks Tab */}
            {activeTab === 'tasks' && (
              <div className="space-y-6">
                <div className="bg-gray-50 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Add New Task</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <input
                      type="text"
                      placeholder="Task name *"
                      value={currentTask.name}
                      onChange={(e) => setCurrentTask({ ...currentTask, name: e.target.value })}
                      className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                    <input
                      type="text"
                      placeholder="Subject (optional)"
                      value={currentTask.subject}
                      onChange={(e) => setCurrentTask({ ...currentTask, subject: e.target.value })}
                      className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                    <input
                      type="number"
                      placeholder="Estimated hours *"
                      value={currentTask.estimatedHours}
                      onChange={(e) => setCurrentTask({ ...currentTask, estimatedHours: e.target.value })}
                      className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                    <input
                      type="date"
                      value={currentTask.deadline}
                      onChange={(e) => setCurrentTask({ ...currentTask, deadline: e.target.value })}
                      className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                    <select
                      value={currentTask.priority}
                      onChange={(e) => setCurrentTask({ ...currentTask, priority: e.target.value })}
                      className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    >
                      <option value="low">Low Priority</option>
                      <option value="medium">Medium Priority</option>
                      <option value="high">High Priority</option>
                    </select>
                    <button
                      onClick={addTask}
                      className="flex items-center justify-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
                    >
                      <Plus size={18} />
                      Add Task
                    </button>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Your Tasks</h3>
                  {tasks.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <Calendar size={48} className="mx-auto mb-3 opacity-50" />
                      <p>No tasks added yet. Add your first task above!</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {tasks.map((task) => (
                        <div key={task.id} className="bg-white border border-gray-200 rounded-lg p-4 flex items-center justify-between hover:shadow-md transition">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <h4 className="font-semibold text-gray-800">{task.name}</h4>
                              <span className={`px-2 py-1 text-xs rounded-full ${task.priority === 'high' ? 'bg-red-100 text-red-700' :
                                task.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-green-100 text-green-700'
                                }`}>
                                {task.priority}
                              </span>
                            </div>
                            <div className="flex gap-4 text-sm text-gray-600">
                              {task.subject && <span>📚 {task.subject}</span>}
                              <span className="flex items-center gap-1">
                                <Clock size={14} />
                                {task.estimatedHours}h
                              </span>
                              <span>📅 Due: {new Date(task.deadline).toLocaleDateString()}</span>
                            </div>
                          </div>
                          <button
                            onClick={() => removeTask(task.id)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                          >
                            <Trash2 size={18} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {tasks.length > 0 && (
                  <button
                    onClick={generateSchedule}
                    disabled={loading}
                    className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:from-indigo-700 hover:to-purple-700 transition disabled:opacity-50 font-semibold text-lg"
                  >
                    {loading ? (
                      <>
                        <RefreshCw size={20} className="animate-spin" />
                        Generating Schedule...
                      </>
                    ) : (
                      <>
                        <Send size={20} />
                        Generate AI Schedule
                      </>
                    )}
                  </button>
                )}
              </div>
            )}

            {/* Preferences Tab */}
            {activeTab === 'preferences' && (
              <div className="space-y-6">
                <div className="flex items-center gap-3 mb-6">
                  <Settings className="text-indigo-600" size={24} />
                  <h3 className="text-xl font-semibold text-gray-800">Study Preferences</h3>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Preferred Study Windows
                    </label>
                    <input
                      type="text"
                      placeholder="e.g., Weekday afternoons, weekends mornings"
                      value={preferences.studyWindows}
                      onChange={(e) => setPreferences({ ...preferences, studyWindows: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Maximum Daily Study Hours
                    </label>
                    <input
                      type="number"
                      placeholder="e.g., 6"
                      value={preferences.maxDailyHours}
                      onChange={(e) => setPreferences({ ...preferences, maxDailyHours: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Break Pattern
                    </label>
                    <input
                      type="text"
                      placeholder="e.g., 15 min break every hour, 30 min lunch break"
                      value={preferences.breakPattern}
                      onChange={(e) => setPreferences({ ...preferences, breakPattern: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Additional Notes
                    </label>
                    <textarea
                      placeholder="Any other preferences or constraints..."
                      value={preferences.additionalNotes}
                      onChange={(e) => setPreferences({ ...preferences, additionalNotes: e.target.value })}
                      rows={4}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    💡 <strong>Tip:</strong> These preferences will be used by the AI to create a personalized schedule that fits your study style and availability.
                  </p>
                </div>
              </div>
            )}

            {/* Schedule Tab */}
            {activeTab === 'schedule' && (
              <div className="space-y-6">
                {!schedule ? (
                  <div className="text-center py-12 text-gray-500">
                    <Calendar size={48} className="mx-auto mb-3 opacity-50" />
                    <p className="mb-2">No schedule generated yet</p>
                    <p className="text-sm">Add tasks and click "Generate AI Schedule" to get started</p>
                  </div>
                ) : (
                  <>
                    <div className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg p-6 text-white">
                      <h3 className="text-xl font-semibold mb-4">Schedule Summary</h3>
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <p className="text-indigo-100 text-sm">Total Tasks</p>
                          <p className="text-3xl font-bold">{schedule.summary.totalTasks}</p>
                        </div>
                        <div>
                          <p className="text-indigo-100 text-sm">Total Hours</p>
                          <p className="text-3xl font-bold">{schedule.summary.totalHours}</p>
                        </div>
                        <div>
                          <p className="text-indigo-100 text-sm">Days Scheduled</p>
                          <p className="text-3xl font-bold">{schedule.summary.daysUsed}</p>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-lg font-semibold text-gray-800 mb-4">Scheduled Sessions</h3>
                      <div className="space-y-3">
                        {schedule.events.map((event, idx) => (
                          <div key={idx} className="bg-white border-l-4 border-indigo-500 rounded-lg p-4 hover:shadow-md transition">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <h4 className="font-semibold text-gray-800 mb-1">{event.taskName}</h4>
                                <div className="flex gap-4 text-sm text-gray-600">
                                  <span>📅 {event.date}</span>
                                  <span className="flex items-center gap-1">
                                    <Clock size={14} />
                                    {event.startTime} ({event.duration}h)
                                  </span>
                                  {event.type && <span>📚 {event.type}</span>}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <button
                      className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition font-semibold"
                    >
                      📅 Export to Google Calendar
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}