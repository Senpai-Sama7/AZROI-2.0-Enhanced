import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import * as d3 from 'd3';
import {
  UserIcon,
  ArrowRightIcon,
  ChatBubbleLeftRightIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import type { CrewAgent, CrewTask, AgentCollaboration } from '../../types/crewai';

interface CollaborationGraphProps {
  agents: CrewAgent[];
  tasks: CrewTask[];
  sessionId: string;
  collaborations?: AgentCollaboration[];
  className?: string;
}

const CollaborationGraph: React.FC<CollaborationGraphProps> = ({
  agents,
  tasks,
  sessionId,
  collaborations = [],
  className = ''
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'agents' | 'tasks' | 'mixed'>('agents');

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 800;
    const height = 600;
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };

    // Create the main group
    const g = svg
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Prepare nodes and links based on view mode
    let nodes: any[] = [];
    let links: any[] = [];

    if (viewMode === 'agents' || viewMode === 'mixed') {
      // Add agent nodes
      nodes = agents.map(agent => ({
        id: agent.id,
        name: agent.name,
        type: 'agent',
        role: agent.role,
        status: agent.status,
        x: Math.random() * (width - 2 * margin.left),
        y: Math.random() * (height - 2 * margin.top)
      }));

      // Add collaboration links
      collaborations.forEach(collab => {
        links.push({
          source: collab.from_agent_id,
          target: collab.to_agent_id,
          type: 'collaboration',
          message_type: collab.message_type,
          weight: 1
        });
      });
    }

    if (viewMode === 'tasks' || viewMode === 'mixed') {
      // Add task nodes
      const taskNodes = tasks.map(task => ({
        id: task.id,
        name: task.title,
        type: 'task',
        status: task.status,
        priority: task.priority,
        agent_id: task.agent_id,
        x: Math.random() * (width - 2 * margin.left),
        y: Math.random() * (height - 2 * margin.top)
      }));

      if (viewMode === 'mixed') {
        nodes = [...nodes, ...taskNodes];
        
        // Add agent-task links
        tasks.forEach(task => {
          links.push({
            source: task.agent_id,
            target: task.id,
            type: 'assignment',
            weight: 1
          });
        });

        // Add task dependency links
        tasks.forEach(task => {
          task.dependencies.forEach(depId => {
            links.push({
              source: depId,
              target: task.id,
              type: 'dependency',
              weight: 1
            });
          });
        });
      } else {
        nodes = taskNodes;
        
        // Add dependency links for tasks-only view
        tasks.forEach(task => {
          task.dependencies.forEach(depId => {
            links.push({
              source: depId,
              target: task.id,
              type: 'dependency',
              weight: 1
            });
          });
        });
      }
    }

    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d: any) => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter((width - 2 * margin.left) / 2, (height - 2 * margin.top) / 2))
      .force('collision', d3.forceCollide().radius(40));

    // Create arrow markers for directed edges
    const defs = g.append('defs');
    
    defs.append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 25)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#666');

    // Create links
    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .enter().append('line')
      .attr('stroke', (d: any) => {
        switch (d.type) {
          case 'collaboration': return '#60A5FA';
          case 'assignment': return '#34D399';
          case 'dependency': return '#F59E0B';
          default: return '#666';
        }
      })
      .attr('stroke-width', (d: any) => Math.sqrt(d.weight) * 2)
      .attr('stroke-opacity', 0.6)
      .attr('marker-end', 'url(#arrowhead)');

    // Create node groups
    const node = g.append('g')
      .attr('class', 'nodes')
      .selectAll('.node')
      .data(nodes)
      .enter().append('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .call(d3.drag<any, any>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }));

    // Add circles for nodes
    node.append('circle')
      .attr('r', (d: any) => d.type === 'agent' ? 25 : 20)
      .attr('fill', (d: any) => {
        if (d.type === 'agent') {
          switch (d.status) {
            case 'executing': return '#3B82F6';
            case 'thinking': return '#8B5CF6';
            case 'collaborating': return '#06B6D4';
            case 'completed': return '#10B981';
            case 'error': return '#EF4444';
            default: return '#6B7280';
          }
        } else {
          switch (d.status) {
            case 'in_progress': return '#3B82F6';
            case 'completed': return '#10B981';
            case 'failed': return '#EF4444';
            case 'review': return '#F59E0B';
            default: return '#6B7280';
          }
        }
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .on('mouseover', (event, d: any) => {
        setHoveredNode(d.id);
      })
      .on('mouseout', () => {
        setHoveredNode(null);
      })
      .on('click', (event, d: any) => {
        setSelectedNode(selectedNode === d.id ? null : d.id);
      });

    // Add icons to nodes
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '.35em')
      .attr('font-size', '12px')
      .attr('fill', 'white')
      .text((d: any) => d.type === 'agent' ? '👤' : '📋');

    // Add labels
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', (d: any) => d.type === 'agent' ? 40 : 35)
      .attr('font-size', '10px')
      .attr('fill', '#fff')
      .text((d: any) => d.name.length > 15 ? d.name.substring(0, 15) + '...' : d.name);

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node
        .attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [agents, tasks, collaborations, viewMode]);

  const getNodeDetails = (nodeId: string) => {
    const agent = agents.find(a => a.id === nodeId);
    if (agent) {
      return {
        type: 'agent',
        name: agent.name,
        role: agent.role,
        status: agent.status,
        current_task: agent.current_task,
        tools: agent.tools.length,
        capabilities: agent.capabilities.length
      };
    }

    const task = tasks.find(t => t.id === nodeId);
    if (task) {
      const assignedAgent = agents.find(a => a.id === task.agent_id);
      return {
        type: 'task',
        name: task.title,
        status: task.status,
        priority: task.priority,
        agent: assignedAgent?.name,
        dependencies: task.dependencies.length,
        tools_used: task.tools_used?.length || 0
      };
    }

    return null;
  };

  return (
    <div className={`collaboration-graph ${className}`}>
      {/* Controls */}
      <div className="mb-6 glass-card p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h3 className="text-lg font-semibold text-white">Collaboration Network</h3>
            <div className="flex space-x-1 bg-black/20 rounded-lg p-1">
              {[
                { id: 'agents', label: 'Agents', icon: UserIcon },
                { id: 'tasks', label: 'Tasks', icon: ClockIcon },
                { id: 'mixed', label: 'Mixed', icon: ChatBubbleLeftRightIcon }
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setViewMode(id as any)}
                  className={`flex items-center space-x-2 px-3 py-1 rounded-md text-sm font-medium transition-all ${
                    viewMode === id
                      ? 'bg-blue-500 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-white/10'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="text-sm text-gray-300">
            {agents.length} agents • {tasks.length} tasks • {collaborations.length} collaborations
          </div>
        </div>
      </div>

      {/* Graph Container */}
      <div className="glass-card p-6">
        <div className="flex">
          <div className="flex-1">
            <svg
              ref={svgRef}
              className="w-full h-[600px] bg-black/10 rounded-lg"
            />
          </div>

          {/* Details Panel */}
          {(selectedNode || hoveredNode) && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="w-80 ml-6"
            >
              <NodeDetailsPanel
                nodeId={selectedNode || hoveredNode!}
                details={getNodeDetails(selectedNode || hoveredNode!)}
                onClose={() => setSelectedNode(null)}
              />
            </motion.div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 glass-card p-4">
        <h4 className="text-sm font-semibold text-white mb-3">Legend</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div className="space-y-2">
            <div className="font-medium text-gray-300">Node Types</div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-blue-500 rounded-full" />
              <span className="text-gray-400">Agent</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-gray-500 rounded-full" />
              <span className="text-gray-400">Task</span>
            </div>
          </div>

          <div className="space-y-2">
            <div className="font-medium text-gray-300">Agent Status</div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full" />
              <span className="text-gray-400">Executing</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-purple-500 rounded-full" />
              <span className="text-gray-400">Thinking</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full" />
              <span className="text-gray-400">Completed</span>
            </div>
          </div>

          <div className="space-y-2">
            <div className="font-medium text-gray-300">Task Status</div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full" />
              <span className="text-gray-400">In Progress</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-yellow-500 rounded-full" />
              <span className="text-gray-400">Review</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-red-500 rounded-full" />
              <span className="text-gray-400">Failed</span>
            </div>
          </div>

          <div className="space-y-2">
            <div className="font-medium text-gray-300">Connections</div>
            <div className="flex items-center space-x-2">
              <div className="w-6 h-0.5 bg-blue-400" />
              <span className="text-gray-400">Collaboration</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-6 h-0.5 bg-green-400" />
              <span className="text-gray-400">Assignment</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-6 h-0.5 bg-yellow-400" />
              <span className="text-gray-400">Dependency</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Node Details Panel Component
const NodeDetailsPanel: React.FC<{
  nodeId: string;
  details: any;
  onClose: () => void;
}> = ({ nodeId, details, onClose }) => {
  if (!details) return null;

  return (
    <div className="glass-card p-4">
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">
          {details.type === 'agent' ? '👤' : '📋'} {details.name}
        </h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white"
        >
          ✕
        </button>
      </div>

      <div className="space-y-3">
        {details.type === 'agent' ? (
          <>
            <div>
              <span className="text-gray-400 text-sm">Role:</span>
              <div className="text-white">{details.role}</div>
            </div>
            <div>
              <span className="text-gray-400 text-sm">Status:</span>
              <div className="text-white capitalize">{details.status}</div>
            </div>
            {details.current_task && (
              <div>
                <span className="text-gray-400 text-sm">Current Task:</span>
                <div className="text-white text-sm">{details.current_task}</div>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-gray-400 text-sm">Tools:</span>
                <div className="text-white">{details.tools}</div>
              </div>
              <div>
                <span className="text-gray-400 text-sm">Capabilities:</span>
                <div className="text-white">{details.capabilities}</div>
              </div>
            </div>
          </>
        ) : (
          <>
            <div>
              <span className="text-gray-400 text-sm">Status:</span>
              <div className="text-white capitalize">{details.status.replace('_', ' ')}</div>
            </div>
            <div>
              <span className="text-gray-400 text-sm">Priority:</span>
              <div className={`inline-block px-2 py-1 rounded text-xs ${
                details.priority === 'critical' ? 'bg-red-500 text-white' :
                details.priority === 'high' ? 'bg-orange-500 text-white' :
                details.priority === 'medium' ? 'bg-yellow-500 text-black' :
                'bg-green-500 text-white'
              }`}>
                {details.priority}
              </div>
            </div>
            {details.agent && (
              <div>
                <span className="text-gray-400 text-sm">Assigned Agent:</span>
                <div className="text-white">{details.agent}</div>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-gray-400 text-sm">Dependencies:</span>
                <div className="text-white">{details.dependencies}</div>
              </div>
              <div>
                <span className="text-gray-400 text-sm">Tools Used:</span>
                <div className="text-white">{details.tools_used}</div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default CollaborationGraph;
