// API基础URL
const API_BASE = '/api';

// 当前选中的数据库
let currentDatabase = null;
// 注意：chatHistory 不再在前端维护，而是从后端获取

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadDatabases();
});

// 加载数据库列表
async function loadDatabases() {
    try {
        const response = await fetch(`${API_BASE}/databases`);
        const databases = await response.json();
        
        // 更新数据库列表
        const databaseList = document.getElementById('databaseList');
        databaseList.innerHTML = '';
        
        databases.forEach(db => {
            const dbItem = document.createElement('div');
            dbItem.className = `database-item ${db.name === currentDatabase ? 'active' : ''}`;
            dbItem.innerHTML = `
                <div class="database-item-name">${db.name}</div>
                <div class="database-item-count">${db.document_count} 文档</div>
                <div class="database-item-actions">
                    <button class="btn btn-secondary" onclick="selectDatabase('${db.name}')" style="width: auto; padding: 5px 10px; font-size: 12px;">选择</button>
                    <button class="btn btn-danger" onclick="deleteDatabase('${db.name}')" style="width: auto; padding: 5px 10px; font-size: 12px;">删除</button>
                </div>
            `;
            databaseList.appendChild(dbItem);
        });
        
        // 更新数据库选择器
        const databaseSelector = document.getElementById('databaseSelector');
        databaseSelector.innerHTML = '<option value="">请选择数据库</option>';
        databases.forEach(db => {
            const option = document.createElement('option');
            option.value = db.name;
            option.textContent = `${db.name} (${db.document_count} 文档)`;
            if (db.name === currentDatabase) {
                option.selected = true;
            }
            databaseSelector.appendChild(option);
        });
        
        // 更新当前数据库信息
        if (currentDatabase) {
            updateDatabaseInfo(currentDatabase);
        } else {
            document.getElementById('currentDatabaseInfo').innerHTML = '<p>请先选择数据库</p>';
        }
    } catch (error) {
        console.error('加载数据库列表失败:', error);
        showMessage('加载数据库列表失败', 'error');
    }
}

// 选择数据库
async function selectDatabase(databaseName) {
    currentDatabase = databaseName;
    await loadDatabases();
    updateDatabaseInfo(databaseName);
    // 加载该数据库的对话历史
    await loadChatHistory(databaseName);
    // 显示/隐藏清除历史按钮
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (databaseName) {
        clearHistoryBtn.style.display = 'block';
    } else {
        clearHistoryBtn.style.display = 'none';
    }
    showMessage(`已切换到数据库: ${databaseName}`, 'success');
}

// 数据库选择器变化
function onDatabaseChange() {
    const selector = document.getElementById('databaseSelector');
    const selectedDatabase = selector.value;
    if (selectedDatabase) {
        selectDatabase(selectedDatabase);
    } else {
        currentDatabase = null;
        document.getElementById('currentDatabaseInfo').innerHTML = '<p>请先选择数据库</p>';
        clearChatMessages();
        // 隐藏清除历史按钮
        document.getElementById('clearHistoryBtn').style.display = 'none';
    }
}

// 更新数据库信息
async function updateDatabaseInfo(databaseName) {
    try {
        const response = await fetch(`${API_BASE}/databases/${databaseName}`);
        const info = await response.json();
        document.getElementById('currentDatabaseInfo').innerHTML = `
            <p><strong>当前数据库:</strong> ${info.name}</p>
            <p><strong>文档数量:</strong> ${info.document_count}</p>
        `;
    } catch (error) {
        console.error('获取数据库信息失败:', error);
    }
}

// 创建数据库
async function createDatabase(event) {
    event.preventDefault();
    const databaseName = document.getElementById('databaseName').value.trim();
    
    if (!databaseName) {
        showMessage('请输入数据库名称', 'error');
        return;
    }
    
    showLoading(true);
    try {
        const response = await fetch(`${API_BASE}/databases`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: databaseName })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('数据库创建成功', 'success');
            closeCreateDatabaseModal();
            await loadDatabases();
            selectDatabase(databaseName);
        } else {
            showMessage(result.detail || '创建数据库失败', 'error');
        }
    } catch (error) {
        console.error('创建数据库失败:', error);
        showMessage('创建数据库失败', 'error');
    } finally {
        showLoading(false);
    }
}

// 删除数据库
async function deleteDatabase(databaseName) {
    if (!confirm(`确定要删除数据库 "${databaseName}" 吗？此操作不可恢复！`)) {
        return;
    }
    
    showLoading(true);
    try {
        const response = await fetch(`${API_BASE}/databases/${databaseName}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showMessage('数据库删除成功', 'success');
            if (currentDatabase === databaseName) {
                currentDatabase = null;
                clearChatMessages();
                document.getElementById('clearHistoryBtn').style.display = 'none';
            }
            await loadDatabases();
        } else {
            const result = await response.json();
            showMessage(result.detail || '删除数据库失败', 'error');
        }
    } catch (error) {
        console.error('删除数据库失败:', error);
        showMessage('删除数据库失败', 'error');
    } finally {
        showLoading(false);
    }
}

// 处理文件上传
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!currentDatabase) {
        showMessage('请先选择数据库', 'error');
        event.target.value = '';
        return;
    }
    
    // 检查文件类型
    const fileExt = file.name.split('.').pop().toLowerCase();
    const supportedFormats = ['txt', 'pdf', 'docx', 'xlsx', 'xls', 'pptx'];
    if (!supportedFormats.includes(fileExt)) {
        showMessage(`不支持的文件格式: .${fileExt}。支持格式: ${supportedFormats.join(', ')}`, 'error');
        event.target.value = '';
        return;
    }
    
    showLoading(true);
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/databases/${currentDatabase}/documents/upload`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(`成功添加 ${result.chunk_count} 个文档块`, 'success');
            await updateDatabaseInfo(currentDatabase);
            await loadDatabases();
        } else {
            showMessage(result.detail || '上传文件失败', 'error');
        }
    } catch (error) {
        console.error('上传文件失败:', error);
        showMessage('上传文件失败: ' + (error.message || '未知错误'), 'error');
    } finally {
        showLoading(false);
        event.target.value = ''; // 清空文件输入
    }
}

// 添加文本
async function addText(event) {
    event.preventDefault();
    const text = document.getElementById('textContent').value.trim();
    
    if (!text) {
        showMessage('请输入文本内容', 'error');
        return;
    }
    
    if (!currentDatabase) {
        showMessage('请先选择数据库', 'error');
        return;
    }
    
    showLoading(true);
    try {
        const response = await fetch(`${API_BASE}/databases/${currentDatabase}/documents/text`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                database_name: currentDatabase,
                text: text,
                source: 'web_input'
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage(`成功添加 ${result.chunk_count} 个文档块`, 'success');
            closeAddTextModal();
            await updateDatabaseInfo(currentDatabase);
            await loadDatabases();
        } else {
            showMessage(result.detail || '添加文本失败', 'error');
        }
    } catch (error) {
        console.error('添加文本失败:', error);
        showMessage('添加文本失败', 'error');
    } finally {
        showLoading(false);
    }
}

// 加载对话历史
async function loadChatHistory(databaseName) {
    try {
        const response = await fetch(`${API_BASE}/databases/${databaseName}/chat/history`);
        const result = await response.json();
        
        if (result.success && result.history && result.history.length > 0) {
            // 清空当前聊天消息
            clearChatMessages();
            
            // 渲染历史消息
            const chatMessages = document.getElementById('chatMessages');
            const welcomeMessage = chatMessages.querySelector('.welcome-message');
            if (welcomeMessage) {
                welcomeMessage.remove();
            }
            
            // 按照历史记录渲染消息
            result.history.forEach(msg => {
                if (msg.role === 'user' || msg.role === 'assistant') {
                    addChatMessage(msg.role, msg.content, false); // false表示不滚动到底部
                }
            });
            
            // 最后滚动到底部
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } else {
            // 没有历史，显示欢迎消息
            clearChatMessages();
        }
    } catch (error) {
        console.error('加载对话历史失败:', error);
        // 如果加载失败，清空消息
        clearChatMessages();
    }
}

// 清除对话历史
async function clearChatHistory() {
    if (!currentDatabase) {
        return;
    }
    
    if (!confirm('确定要清除当前对话历史吗？此操作不可恢复！')) {
        return;
    }
    
    showLoading(true);
    try {
        const response = await fetch(`${API_BASE}/databases/${currentDatabase}/chat/history`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            showMessage('对话历史已清除', 'success');
            clearChatMessages();
        } else {
            showMessage(result.detail || '清除对话历史失败', 'error');
        }
    } catch (error) {
        console.error('清除对话历史失败:', error);
        showMessage('清除对话历史失败', 'error');
    } finally {
        showLoading(false);
    }
}

// 发送消息（流式）
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const query = input.value.trim();
    
    if (!query) {
        return;
    }
    
    if (!currentDatabase) {
        showMessage('请先选择数据库', 'error');
        return;
    }
    
    // 添加用户消息到聊天界面
    addChatMessage('user', query);
    input.value = '';
    
    // 注意：不再在前端维护chatHistory，后端会自动管理
    
    // 创建助手消息容器（用于流式更新）
    const assistantMessageId = 'assistant-' + Date.now();
    const chatMessages = document.getElementById('chatMessages');
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.id = assistantMessageId;
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-header">助手</div>
            <div class="message-text" id="${assistantMessageId}-text">
                <div class="thinking-section" id="${assistantMessageId}-thinking" style="display: none;">
                    <div class="thinking-header">思考过程：</div>
                    <div class="thinking-content" id="${assistantMessageId}-thinking-content"></div>
                </div>
                <div class="answer-section" id="${assistantMessageId}-answer"></div>
            </div>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    const answerElement = document.getElementById(`${assistantMessageId}-answer`);
    const thinkingElement = document.getElementById(`${assistantMessageId}-thinking`);
    const thinkingContentElement = document.getElementById(`${assistantMessageId}-thinking-content`);
    
    let fullContent = '';
    let thinkingContent = '';
    let retrievedDocs = [];
    
    try {
        const response = await fetch(`${API_BASE}/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                database_name: currentDatabase,
                query: query,
                n_results: 5,
                history: [] // 不发送历史，后端会自动管理
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // 保留最后不完整的行
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.type === 'documents') {
                            // 显示检索到的文档
                            retrievedDocs = data.documents || [];
                            if (retrievedDocs.length > 0) {
                                const docsHtml = `
                                    <div class="retrieved-docs">
                                        <div class="retrieved-docs-title">参考文档 (${retrievedDocs.length}):</div>
                                        ${retrievedDocs.map((doc, idx) => `
                                            <div class="retrieved-doc-item">
                                                <strong>文档 ${idx + 1}:</strong> ${escapeHtml(doc.content.substring(0, 100))}...
                                            </div>
                                        `).join('')}
                                    </div>
                                `;
                                answerElement.innerHTML = docsHtml;
                            }
                        } else if (data.type === 'thinking') {
                            // 显示思考过程
                            thinkingContent = data.content || '';
                            if (thinkingContent) {
                                thinkingElement.style.display = 'block';
                                // 使用Markdown渲染思考过程
                                thinkingContentElement.innerHTML = DOMPurify.sanitize(marked.parse(thinkingContent));
                            }
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        } else if (data.type === 'content') {
                            // 显示内容（实时更新）
                            fullContent = data.full_content || data.content || '';
                            // 使用Markdown渲染内容
                            const markdownHtml = marked.parse(fullContent);
                            const sanitizedHtml = DOMPurify.sanitize(markdownHtml);
                            
                            // 更新回答部分
                            let answerHtml = '';
                            if (retrievedDocs.length > 0) {
                                answerHtml = `
                                    <div class="retrieved-docs">
                                        <div class="retrieved-docs-title">参考文档 (${retrievedDocs.length}):</div>
                                        ${retrievedDocs.map((doc, idx) => `
                                            <div class="retrieved-doc-item">
                                                <strong>文档 ${idx + 1}:</strong> ${escapeHtml(doc.content.substring(0, 100))}...
                                            </div>
                                        `).join('')}
                                    </div>
                                `;
                            }
                            answerHtml += `<div class="answer-content">${sanitizedHtml}</div>`;
                            answerElement.innerHTML = answerHtml;
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        } else if (data.type === 'done') {
                            // 完成
                            fullContent = data.full_content || fullContent;
                            thinkingContent = data.thinking || thinkingContent;
                            
                            // 最终渲染
                            if (thinkingContent) {
                                thinkingElement.style.display = 'block';
                                thinkingContentElement.innerHTML = DOMPurify.sanitize(marked.parse(thinkingContent));
                            }
                            
                            const markdownHtml = marked.parse(fullContent);
                            const sanitizedHtml = DOMPurify.sanitize(markdownHtml);
                            
                            let answerHtml = '';
                            if (retrievedDocs.length > 0) {
                                answerHtml = `
                                    <div class="retrieved-docs">
                                        <div class="retrieved-docs-title">参考文档 (${retrievedDocs.length}):</div>
                                        ${retrievedDocs.map((doc, idx) => `
                                            <div class="retrieved-doc-item">
                                                <strong>文档 ${idx + 1}:</strong> ${escapeHtml(doc.content.substring(0, 100))}...
                                            </div>
                                        `).join('')}
                                    </div>
                                `;
                            }
                            answerHtml += `<div class="answer-content">${sanitizedHtml}</div>`;
                            answerElement.innerHTML = answerHtml;
                            
                            // 注意：历史由后端管理，不需要在前端添加
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                            break;
                        } else if (data.type === 'error') {
                            // 错误
                            answerElement.innerHTML = `<div class="error-message">${escapeHtml(data.content)}</div>`;
                            break;
                        }
                    } catch (e) {
                        console.error('解析SSE数据失败:', e, line);
                    }
                }
            }
        }
    } catch (error) {
        console.error('发送消息失败:', error);
        answerElement.innerHTML = '<div class="error-message">发送消息失败，请稍后重试</div>';
    }
}

// HTML转义函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 添加聊天消息
function addChatMessage(role, content, scrollToBottom = true) {
    const chatMessages = document.getElementById('chatMessages');
    
    // 移除欢迎消息
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    // 如果是助手消息且包含HTML，直接使用；否则渲染Markdown
    let renderedContent = content;
    if (role === 'assistant' && typeof marked !== 'undefined') {
        // 检查是否已经是HTML
        if (!content.includes('<div') && !content.includes('<span')) {
            try {
                // 渲染Markdown
                const markdownHtml = marked.parse(content);
                renderedContent = DOMPurify.sanitize(markdownHtml);
            } catch (e) {
                console.error('Markdown渲染失败:', e);
                renderedContent = escapeHtml(content);
            }
        }
    } else if (role === 'user') {
        // 用户消息直接转义，不渲染Markdown
        renderedContent = escapeHtml(content);
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-header">${role === 'user' ? '您' : '助手'}</div>
            <div class="message-text ${role === 'assistant' ? 'answer-content' : ''}">${renderedContent}</div>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    if (scrollToBottom) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// 清空聊天消息
function clearChatMessages() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <h4>欢迎使用RAG系统</h4>
            <p>请先选择一个数据库，然后开始对话</p>
        </div>
    `;
}

// 处理聊天输入框按键
function handleChatInputKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// 显示/隐藏加载提示
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}

// 显示消息提示
function showMessage(message, type = 'info') {
    // 创建消息提示元素
    const messageDiv = document.createElement('div');
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'error' ? '#e53e3e' : type === 'success' ? '#48bb78' : '#4299e1'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 3000;
        animation: slideIn 0.3s ease-out;
        max-width: 300px;
    `;
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    // 3秒后自动移除
    setTimeout(() => {
        messageDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 300);
    }, 3000);
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// 模态框控制
function showCreateDatabaseModal() {
    document.getElementById('createDatabaseModal').style.display = 'block';
    document.getElementById('databaseName').value = '';
}

function closeCreateDatabaseModal() {
    document.getElementById('createDatabaseModal').style.display = 'none';
}

function showAddTextModal() {
    if (!currentDatabase) {
        showMessage('请先选择数据库', 'error');
        return;
    }
    document.getElementById('addTextModal').style.display = 'block';
    document.getElementById('textContent').value = '';
}

function closeAddTextModal() {
    document.getElementById('addTextModal').style.display = 'none';
}

// 点击模态框外部关闭
window.onclick = function(event) {
    const createModal = document.getElementById('createDatabaseModal');
    const addTextModal = document.getElementById('addTextModal');
    
    if (event.target === createModal) {
        closeCreateDatabaseModal();
    }
    if (event.target === addTextModal) {
        closeAddTextModal();
    }
}

