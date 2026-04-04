import React from 'react';

interface Task {
  id: number;
  text: string;
  completed: boolean;
}

interface TaskProps {
  task: Task;
  onComplete: (id: number) => void;
  onDelete: (id: number) => void;
}

const Task: React.FC<TaskProps> = ({ task, onComplete, onDelete }) => {
  return (
    <div style={{ textDecoration: task.completed ? 'line-through' : 'none' }}>
      <input type="checkbox" checked={task.completed} onChange={() => onComplete(task.id)} />
      <span>{task.text}</span>
      <button onClick={() => onDelete(task.id)}>Delete</button>
    </div>
  );
};

export default Task;