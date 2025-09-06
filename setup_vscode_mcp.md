# Настройка VS Code MCP для Claude

## 1. Установка MCP сервера для VS Code

### Шаг 1: Установите Node.js (если нет)
```powershell
# Проверка
node --version
npm --version
```

### Шаг 2: Установите VS Code MCP Server
```bash
npm install -g @modelcontextprotocol/server-vscode
```

### Шаг 3: Настройте MCP в Claude Desktop

Откройте файл конфигурации Claude Desktop:
`%APPDATA%\Claude\claude_desktop_config.json`

Добавьте в секцию "mcpServers":

```json
{
  "mcpServers": {
    "vscode": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-vscode"
      ],
      "env": {
        "VSCODE_WORKSPACE": "C:\\Users\\konfu\\Desktop\\Sites\\Experiment\\Experiment1\\WalletSender_MCP  копия\\WalletSender_Modular"
      }
    }
  }
}
```

### Шаг 4: Перезапустите Claude Desktop

## 2. Альтернатива: Прямая интеграция через PowerShell

Так как у вас уже работает Windows-MCP, можно управлять VS Code через PowerShell:

```powershell
# Открыть файл в VS Code
code "путь_к_файлу"

# Открыть папку
code "путь_к_папке"

# Установить расширение
code --install-extension ms-python.python

# Открыть файл на определенной строке
code --goto "файл.py:100"
```

## 3. Создание кастомного MCP сервера для VS Code

Создайте файл `vscode-mcp-server.js`:

```javascript
#!/usr/bin/env node

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { exec } = require('child_process');
const fs = require('fs').promises;
const path = require('path');

class VSCodeMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'vscode-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupHandlers();
  }

  setupHandlers() {
    // Инструменты для управления VS Code
    this.server.setRequestHandler('tools/list', async () => ({
      tools: [
        {
          name: 'vscode_open_file',
          description: 'Open a file in VS Code',
          inputSchema: {
            type: 'object',
            properties: {
              filepath: { type: 'string', description: 'Path to file' },
              line: { type: 'number', description: 'Line number (optional)' }
            },
            required: ['filepath']
          }
        },
        {
          name: 'vscode_edit_file',
          description: 'Edit a file in VS Code',
          inputSchema: {
            type: 'object',
            properties: {
              filepath: { type: 'string' },
              content: { type: 'string' },
              line: { type: 'number' }
            },
            required: ['filepath', 'content']
          }
        },
        {
          name: 'vscode_run_command',
          description: 'Run VS Code command',
          inputSchema: {
            type: 'object',
            properties: {
              command: { type: 'string' }