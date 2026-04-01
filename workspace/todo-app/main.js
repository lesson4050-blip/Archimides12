const taskList = document.getElementById('tasks');
const taskInput = document.getElementById('task');
const addBtn = document.getElementById('add');
const deleteBtn = document.getElementById('delete');

let tasks = [];

addBtn.addEventListener('click', () => {
    const task = taskInput.value;
    if (task) {
        tasks.push(task);
        taskInput.value = '';
        renderTaskList();
    }
});

deleteBtn.addEventListener('click', () => {
    tasks.pop();
    renderTaskList();
});

function renderTaskList() {
    const taskHtml = tasks.map((task, index) => `<li>${task}<button onclick='completeTask(${index})'>Complete</button></li>`).join('');
    taskList.innerHTML = taskHtml;
}

function completeTask(index) {
    tasks[index] = tasks[index] + ' (Completed)';
    renderTaskList();
}