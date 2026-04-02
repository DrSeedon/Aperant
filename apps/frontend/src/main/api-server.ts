/**
 * Local HTTP API for external tools (MCP server, CLI) to trigger Aperant operations.
 *
 * Listens on 127.0.0.1 only. Port written to ~/.config/aperant/api-port.
 * MCP server reads the port file and sends requests.
 *
 * Endpoints:
 *   POST /api/tasks/start  { projectId?, specId, model?, skipQa?, direct? }
 *   POST /api/tasks/stop   { taskId }
 */

import { createServer, IncomingMessage, ServerResponse } from 'http';
import { writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';
import { app } from 'electron';
import type { AgentManager } from './agent/agent-manager';
import { projectStore } from './project-store';
import { initializeClaudeProfileManager } from './claude-profile-manager';

let server: ReturnType<typeof createServer> | null = null;
let apiPort = 0;

function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk: string) => { data += chunk; });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

function json(res: ServerResponse, status: number, body: Record<string, unknown>) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(body));
}

function findTask(specId: string, projectDir?: string) {
  const projects = projectStore.getProjects();
  for (const project of projects) {
    if (projectDir && project.path !== projectDir) continue;
    const tasks = projectStore.getTasks(project.id);
    const task = tasks.find(t => t.specId === specId || t.specId.startsWith(specId));
    if (task) return { task, project };
  }
  return null;
}

export function startApiServer(agentManager: AgentManager): void {
  server = createServer(async (req, res) => {
    // CORS for local tools
    res.setHeader('Access-Control-Allow-Origin', '127.0.0.1');

    if (req.method === 'OPTIONS') {
      res.writeHead(204);
      res.end();
      return;
    }

    try {
      const url = req.url || '';
      const body = req.method === 'POST' ? JSON.parse(await readBody(req) || '{}') : {};

      // POST /api/tasks/start
      if (url === '/api/tasks/start' && req.method === 'POST') {
        const { specId, projectDir, model, skipQa, direct, baseBranch } = body;

        if (!specId) {
          json(res, 400, { error: 'specId is required' });
          return;
        }

        const found = findTask(specId, projectDir);
        if (!found) {
          json(res, 404, { error: `Task ${specId} not found` });
          return;
        }

        const { task, project } = found;

        // Build options
        const options = {
          parallel: false,
          workers: 1,
          baseBranch: baseBranch || task.metadata?.baseBranch as string || project.settings?.mainBranch,
          useWorktree: task.metadata?.useWorktree !== false,
          useLocalBranch: task.metadata?.useLocalBranch as boolean | undefined,
        };

        // Update model in metadata if provided
        if (model && task.metadata) {
          task.metadata.model = model;
        }

        // Ensure OAuth credentials are available
        try {
          const profileManager = await initializeClaudeProfileManager();
          if (!profileManager.hasValidAuth()) {
            json(res, 401, { error: 'No valid Claude authentication. Open Aperant Settings > Claude Profiles.' });
            return;
          }
        } catch (authErr) {
          json(res, 500, { error: `Auth init failed: ${authErr}` });
          return;
        }

        try {
          await agentManager.startTaskExecution(
            task.id,
            project.path,
            task.specId,
            options,
            project.id,
          );
          json(res, 200, { success: true, taskId: task.id, specId: task.specId });
        } catch (err) {
          json(res, 500, { error: `Failed to start: ${err}` });
        }
        return;
      }

      // POST /api/tasks/stop
      if (url === '/api/tasks/stop' && req.method === 'POST') {
        const { taskId } = body;
        if (!taskId) {
          json(res, 400, { error: 'taskId is required' });
          return;
        }
        try {
          await agentManager.killProcess(taskId);
          json(res, 200, { success: true });
        } catch (err) {
          json(res, 500, { error: `Failed to stop: ${err}` });
        }
        return;
      }

      // GET /api/health
      if (url === '/api/health') {
        json(res, 200, { status: 'ok', port: apiPort });
        return;
      }

      json(res, 404, { error: 'Not found' });
    } catch (err) {
      json(res, 500, { error: `Internal error: ${err}` });
    }
  });

  // Listen on random port, 127.0.0.1 only
  server.listen(0, '127.0.0.1', () => {
    const addr = server!.address();
    if (addr && typeof addr === 'object') {
      apiPort = addr.port;
      // Write port to well-known location so MCP server can find it
      const portDir = join(app.getPath('userData'));
      mkdirSync(portDir, { recursive: true });
      const portFile = join(portDir, 'api-port');
      writeFileSync(portFile, String(apiPort), 'utf-8');
      console.log(`[API] Local API server listening on 127.0.0.1:${apiPort}`);
      console.log(`[API] Port file: ${portFile}`);
    }
  });

  server.on('error', (err) => {
    console.error('[API] Server error:', err);
  });
}

export function stopApiServer(): void {
  if (server) {
    server.close();
    server = null;
    console.log('[API] Server stopped');
  }
}
