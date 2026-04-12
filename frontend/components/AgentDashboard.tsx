import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { X } from 'lucide-react';

interface Task {
  task_id: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  result?: any;
}

interface AgentStatus {
  agent_id: string;
  state: string;
  active_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  uptime: number;
}

interface DashboardProps {
  onClose: () => void;
}

const AgentDashboard: React.FC<DashboardProps> = ({ onClose }) => {
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTaskDescription, setNewTaskDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [statistics, setStatistics] = useState<any>(null);

  useEffect(() => {
    // Загрузить статус агента
    fetchAgentStatus();
    fetchTasks();
    fetchStatistics();

    // Обновлять каждые 5 секунд
    const interval = setInterval(() => {
      fetchAgentStatus();
      fetchTasks();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const fetchAgentStatus = async () => {
    try {
      const response = await fetch('/api/v1/agent/status');
      const data = await response.json();
      setAgentStatus(data);
    } catch (error) {
      console.error('Ошибка загрузки статуса:', error);
    }
  };

  const fetchTasks = async () => {
    try {
      const response = await fetch('/api/v1/tasks?limit=50');
      const data = await response.json();
      setTasks(data.tasks);
    } catch (error) {
      console.error('Ошибка загрузки задач:', error);
    }
  };

  const fetchStatistics = async () => {
    try {
      const response = await fetch('/api/v1/statistics');
      const data = await response.json();
      setStatistics(data);
    } catch (error) {
      console.error('Ошибка загрузки статистики:', error);
    }
  };

  const createTask = async () => {
    if (!newTaskDescription.trim()) return;

    setLoading(true);
    try {
      const response = await fetch('/api/v1/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: newTaskDescription,
          priority: 1,
          timeout: 300
        })
      });

      if (response.ok) {
        setNewTaskDescription('');
        fetchTasks();
      }
    } catch (error) {
      console.error('Ошибка создания задачи:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return '#10b981';
      case 'failed':
        return '#ef4444';
      case 'running':
        return '#3b82f6';
      case 'pending':
        return '#f59e0b';
      default:
        return '#6b7280';
    }
  };

  const chartData = [
    { name: 'Пн', completed: 12, failed: 2 },
    { name: 'Вт', completed: 19, failed: 1 },
    { name: 'Ср', completed: 15, failed: 3 },
    { name: 'Чт', completed: 25, failed: 2 },
    { name: 'Пт', completed: 22, failed: 1 },
    { name: 'Сб', completed: 18, failed: 2 },
    { name: 'Вс', completed: 20, failed: 1 }
  ];

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 50, padding: '20px', backgroundColor: '#0f172a', color: '#e2e8f0', overflowY: 'auto' }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Заголовок */}
        <div style={{ marginBottom: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: '32px', fontWeight: 'bold', margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ color: '#3b82f6' }}>⊕</span> Archimedes COSMO Dashboard
            </h1>
            <p style={{ color: '#94a3b8', margin: '0' }}>
              Автономный ИИ-агент enterprise-уровня
            </p>
          </div>
          <button 
            onClick={onClose}
            className="hover:bg-[#1e293b] text-[#94a3b8] hover:text-white transition-colors"
            style={{ 
              background: 'transparent', border: '1px solid #334155', cursor: 'pointer',
              padding: '8px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}
          >
            <X size={24} />
          </button>
        </div>

        {/* Статус агента */}
        {agentStatus && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '20px',
            marginBottom: '30px'
          }}>
            <div style={{
              backgroundColor: '#1e293b',
              padding: '20px',
              borderRadius: '8px',
              border: '1px solid #334155'
            }}>
              <div style={{ color: '#94a3b8', fontSize: '14px' }}>Состояние</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#10b981', marginTop: '8px' }}>
                {agentStatus.state.toUpperCase()}
              </div>
            </div>

            <div style={{
              backgroundColor: '#1e293b',
              padding: '20px',
              borderRadius: '8px',
              border: '1px solid #334155'
            }}>
              <div style={{ color: '#94a3b8', fontSize: '14px' }}>Активных задач</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#3b82f6', marginTop: '8px' }}>
                {agentStatus.active_tasks}
              </div>
            </div>

            <div style={{
              backgroundColor: '#1e293b',
              padding: '20px',
              borderRadius: '8px',
              border: '1px solid #334155'
            }}>
              <div style={{ color: '#94a3b8', fontSize: '14px' }}>Завершено</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#10b981', marginTop: '8px' }}>
                {agentStatus.completed_tasks}
              </div>
            </div>

            <div style={{
              backgroundColor: '#1e293b',
              padding: '20px',
              borderRadius: '8px',
              border: '1px solid #334155'
            }}>
              <div style={{ color: '#94a3b8', fontSize: '14px' }}>Ошибок</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ef4444', marginTop: '8px' }}>
                {agentStatus.failed_tasks}
              </div>
            </div>
          </div>
        )}

        {/* Создание новой задачи */}
        <div style={{
          backgroundColor: '#1e293b',
          padding: '20px',
          borderRadius: '8px',
          border: '1px solid #334155',
          marginBottom: '30px'
        }}>
          <h2 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 15px 0' }}>
            📋 Создать новую задачу
          </h2>
          <div style={{ display: 'flex', gap: '10px' }}>
            <input
              type="text"
              value={newTaskDescription}
              onChange={(e) => setNewTaskDescription(e.target.value)}
              placeholder="Описание задачи..."
              style={{
                flex: 1,
                padding: '10px 15px',
                backgroundColor: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '6px',
                color: '#e2e8f0',
                fontSize: '14px'
              }}
              onKeyPress={(e) => e.key === 'Enter' && createTask()}
            />
            <button
              onClick={createTask}
              disabled={loading}
              style={{
                padding: '10px 20px',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 'bold',
                opacity: loading ? 0.6 : 1
              }}
            >
              {loading ? 'Отправка...' : 'Отправить'}
            </button>
          </div>
        </div>

        {/* Графики */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))',
          gap: '20px',
          marginBottom: '30px'
        }}>
          <div style={{
            backgroundColor: '#1e293b',
            padding: '20px',
            borderRadius: '8px',
            border: '1px solid #334155'
          }}>
            <h3 style={{ margin: '0 0 15px 0', fontSize: '16px', fontWeight: 'bold' }}>
              📊 Выполнение задач
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155' }} />
                <Legend />
                <Bar dataKey="completed" fill="#10b981" name="Завершено" />
                <Bar dataKey="failed" fill="#ef4444" name="Ошибок" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div style={{
            backgroundColor: '#1e293b',
            padding: '20px',
            borderRadius: '8px',
            border: '1px solid #334155'
          }}>
            <h3 style={{ margin: '0 0 15px 0', fontSize: '16px', fontWeight: 'bold' }}>
              📈 Тренд производительности
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155' }} />
                <Legend />
                <Line type="monotone" dataKey="completed" stroke="#10b981" name="Завершено" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Список задач */}
        <div style={{
          backgroundColor: '#1e293b',
          padding: '20px',
          borderRadius: '8px',
          border: '1px solid #334155'
        }}>
          <h2 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 15px 0' }}>
            📝 Недавние задачи
          </h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <th style={{ textAlign: 'left', padding: '10px', color: '#94a3b8' }}>ID</th>
                  <th style={{ textAlign: 'left', padding: '10px', color: '#94a3b8' }}>Описание</th>
                  <th style={{ textAlign: 'left', padding: '10px', color: '#94a3b8' }}>Статус</th>
                  <th style={{ textAlign: 'left', padding: '10px', color: '#94a3b8' }}>Создано</th>
                </tr>
              </thead>
              <tbody>
                {tasks.slice(0, 10).map((task) => (
                  <tr key={task.task_id} style={{ borderBottom: '1px solid #334155' }}>
                    <td style={{ padding: '10px', fontSize: '12px', color: '#94a3b8' }}>
                      {task.task_id.substring(0, 8)}...
                    </td>
                    <td style={{ padding: '10px' }}>
                      {task.description.substring(0, 50)}...
                    </td>
                    <td style={{ padding: '10px' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        backgroundColor: getStatusColor(task.status),
                        color: 'white',
                        fontSize: '12px',
                        fontWeight: 'bold'
                      }}>
                        {task.status}
                      </span>
                    </td>
                    <td style={{ padding: '10px', fontSize: '12px', color: '#94a3b8' }}>
                      {new Date(task.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentDashboard;
