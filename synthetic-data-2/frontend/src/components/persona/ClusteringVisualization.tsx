'use client'

import React, { useEffect, useRef } from 'react'
import * as d3 from 'd3'

interface ClusteringData {
  n_clusters: number
  personas: Array<{
    persona_id: string
    cluster: number
    x: number
    y: number
    age: number
    gender: string
    income: string
    education: string
    location: string
  }>
  cluster_centers: Array<{
    cluster: number
    x: number
    y: number
    size: number
  }>
  algorithm: string
}

interface ClusteringVisualizationProps {
  data: ClusteringData
}

export const ClusteringVisualization: React.FC<ClusteringVisualizationProps> = ({ data }) => {
  const svgRef = useRef<SVGSVGElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!data || !svgRef.current) return

    const svg = d3.select(svgRef.current)
    const tooltip = d3.select(tooltipRef.current)
    
    // Clear previous content
    svg.selectAll('*').remove()
    
    const margin = { top: 20, right: 20, bottom: 40, left: 40 }
    const width = 500 - margin.left - margin.right
    const height = 400 - margin.top - margin.bottom
    
    // Create scales
    const xExtent = d3.extent(data.personas, (d: any) => d.x) as [number, number]
    const yExtent = d3.extent(data.personas, (d: any) => d.y) as [number, number]
    
    const xScale = d3.scaleLinear()
      .domain(xExtent)
      .range([0, width])
      .nice()
    
    const yScale = d3.scaleLinear()
      .domain(yExtent)
      .range([height, 0])
      .nice()
    
    // Color scale for clusters
    const colorScale = d3.scaleOrdinal(d3.schemeCategory10)
    
    // Create main group
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)
    
    // Add axes
    g.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(xScale))
      .append('text')
      .attr('x', width / 2)
      .attr('y', 35)
      .attr('fill', '#9CA3AF')
      .style('text-anchor', 'middle')
      .text('PCA Component 1')
    
    g.append('g')
      .call(d3.axisLeft(yScale))
      .append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -30)
      .attr('x', -height / 2)
      .attr('fill', '#9CA3AF')
      .style('text-anchor', 'middle')
      .text('PCA Component 2')
    
    // Style axes
    g.selectAll('.domain, .tick line')
      .attr('stroke', '#4B5563')
    
    g.selectAll('.tick text')
      .attr('fill', '#9CA3AF')
      .style('font-size', '12px')
    
    // Add cluster centers (larger circles)
    g.selectAll('.cluster-center')
      .data(data.cluster_centers)
      .enter().append('circle')
      .attr('class', 'cluster-center')
      .attr('cx', (d: any) => xScale(d.x))
      .attr('cy', (d: any) => yScale(d.y))
      .attr('r', (d: any) => Math.sqrt(d.size) * 3 + 8)
      .attr('fill', 'none')
      .attr('stroke', (d: any) => colorScale(d.cluster.toString()))
      .attr('stroke-width', 3)
      .attr('stroke-dasharray', '5,5')
      .style('opacity', 0.8)
    
    // Add personas (smaller circles)
    g.selectAll('.persona-point')
      .data(data.personas)
      .enter().append('circle')
      .attr('class', 'persona-point')
      .attr('cx', (d: any) => xScale(d.x))
      .attr('cy', (d: any) => yScale(d.y))
      .attr('r', 6)
      .attr('fill', (d: any) => colorScale(d.cluster.toString()))
      .attr('stroke', '#1F2937')
      .attr('stroke-width', 1)
      .style('opacity', 0.8)
      .style('cursor', 'pointer')
      .on('mouseover', function(event: any, d: any) {
        // Highlight point
        d3.select(this as any)
          .transition()
          .duration(200)
          .attr('r', 8)
          .style('opacity', 1)
        
        // Show tooltip
        tooltip
          .style('opacity', 1)
          .html(`
            <div class="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
              <div class="text-white font-semibold mb-2">Persona ${d.persona_id.slice(0, 8)}...</div>
              <div class="text-gray-300 text-sm space-y-1">
                <div><span class="text-gray-400">Cluster:</span> ${d.cluster}</div>
                <div><span class="text-gray-400">Age:</span> ${d.age}</div>
                <div><span class="text-gray-400">Gender:</span> ${d.gender}</div>
                <div><span class="text-gray-400">Income:</span> ${d.income}</div>
                <div><span class="text-gray-400">Education:</span> ${d.education}</div>
                <div><span class="text-gray-400">Location:</span> ${d.location}</div>
              </div>
            </div>
          `)
          .style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 10) + 'px')
      })
      .on('mouseout', function() {
        // Reset point
        d3.select(this as any)
          .transition()
          .duration(200)
          .attr('r', 6)
          .style('opacity', 0.8)
        
        // Hide tooltip
        tooltip.style('opacity', 0)
      })
    
    // Add legend
    const legend = g.append('g')
      .attr('class', 'legend')
      .attr('transform', `translate(${width - 120}, 20)`)
    
    const legendItems = legend.selectAll('.legend-item')
      .data(data.cluster_centers)
      .enter().append('g')
      .attr('class', 'legend-item')
      .attr('transform', (d: any, i: number) => `translate(0, ${i * 20})`)
    
    legendItems.append('circle')
      .attr('cx', 8)
      .attr('cy', 8)
      .attr('r', 6)
      .attr('fill', (d: any) => colorScale(d.cluster.toString()))
    
    legendItems.append('text')
      .attr('x', 20)
      .attr('y', 8)
      .attr('dy', '0.35em')
      .attr('fill', '#9CA3AF')
      .style('font-size', '12px')
      .text((d: any) => `Cluster ${d.cluster} (${d.size})`)
    
  }, [data])

  return (
    <div className="relative">
      <div className="mb-4">
        <p className="text-sm text-gray-400">
          Visualization shows persona distribution using PCA-reduced features.
          Each point represents a persona, colored by cluster assignment.
        </p>
      </div>
      
      <div className="relative bg-gray-900 rounded-lg p-4">
        <svg
          ref={svgRef}
          width={500}
          height={400}
          className="w-full h-auto"
        />
        
        <div
          ref={tooltipRef}
          className="absolute pointer-events-none opacity-0 transition-opacity duration-200 z-10"
          style={{ position: 'absolute' }}
        />
      </div>
      
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-400">Algorithm:</span>
          <span className="ml-2 text-white">{data.algorithm}</span>
        </div>
        <div>
          <span className="text-gray-400">Clusters:</span>
          <span className="ml-2 text-white">{data.n_clusters}</span>
        </div>
      </div>
    </div>
  )
}