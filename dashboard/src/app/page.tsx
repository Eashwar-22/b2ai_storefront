"use client";

import { useState, useEffect } from "react";
import styles from "./page.module.css";

interface Message {
  node: string;
  content: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inventory, setInventory] = useState<string[]>([]);
  const [prompt, setPrompt] = useState("I want to buy 5 high-end GPUs for $25k");
  const [isNegotiating, setIsNegotiating] = useState(false);

  // fetch inventory on mount
  useEffect(() => {
    const fetchInventory = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/inventory");
        const data = await res.json();
        setInventory(data.products || []);
      } catch (e) {
        console.error("Failed to load inventory", e);
      }
    };
    fetchInventory();
  }, []);

  const startStream = () => {
    setMessages([]);
    setIsNegotiating(true);

    const eventSource = new EventSource(
      `http://127.0.0.1:8000/stream?prompt=${encodeURIComponent(prompt)}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.content && data.content.trim() !== "") {
        setMessages((prev) => [...prev, data]);
      }
      
      // stop if deal closed or error
      if (data.node === "ROI_ENGINE" || data.node === "ERROR") {
        setIsNegotiating(false);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setIsNegotiating(false);
      eventSource.close();
    };
  };

  return (
    <div className={styles.dashboard}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <h1 className={styles.glow}>B2AI COMMAND</h1>
        </div>
        
        <div className={styles.controls}>
          <input 
            type="text" 
            value={prompt} 
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isNegotiating}
            placeholder="Procurement request..."
          />
          <button onClick={startStream} disabled={isNegotiating}>
            {isNegotiating ? "RUNNING..." : "EXECUTE"}
          </button>
        </div>
      </header>

      {/* LEFT: Live Catalog Grounding */}
      <aside className={styles.sidebar}>
        <h2 className={styles.sectionTitle}>Inventory Ledger</h2>
        {inventory.length === 0 && <div className={styles.itemSub}>Synchronizing Catalog...</div>}
        {inventory.map((item, i) => (
          <div key={i} className={styles.inventoryItem}>
            <div className={styles.itemHeader}>
              <span>{item.toUpperCase()}</span>
              <span style={{color: 'var(--accent-success)'}}>IN STOCK</span>
            </div>
            <div className={styles.itemSub}>SKU: B2AI-{(1000 + i).toString()} | CATEGORY: HW_PROCURMENT</div>
          </div>
        ))}
      </aside>

      {/* CENTER: Negotiation Trace */}
      <section className={styles.feed}>
        <div className={styles.contextCard}>
          <h2 className={styles.sectionTitle} style={{marginTop: 0}}>MISSION OVERVIEW</h2>
          <p className={styles.contextText}>
            You are witnessing a live B2B procurement auction. <strong>ALEX</strong> (Our Agent) is competing 
            with <strong>VAPOR</strong> (Competitor) to secure deals with <strong>JORDAN</strong> (Buyer), 
            while adhering to strict inventory grounding and ROI targets.
          </p>
        </div>

        <h2 className={styles.sectionTitle}>Negotiation Trace Log</h2>
        {messages.length === 0 && !isNegotiating && (
          <div style={{ color: "var(--text-secondary)", fontSize: "0.85rem", padding: "12px" }}>
            [SYSTEM]: Awaiting localized prompt to initialize agent graph...
          </div>
        )}
        {messages.map((msg, index) => {
          const nodeName = msg.node.toLowerCase();
          const isROI = msg.node === "ROI_ENGINE";
          const isError = msg.node === "ERROR";
          
          return (
            <div 
              key={index} 
              className={`${styles.logEntry} ${styles[nodeName] || ""} ${isROI ? styles.roi_card : ""} ${isError ? styles.errorEntry : ""}`}
            >
              <div className={styles.nodeLabel}>
                {isROI ? "ANALYTICS" : msg.node}
              </div>
              <div className={styles.content}>
                {isROI && <strong style={{color: 'var(--accent-success)', display: 'block', marginBottom: '4px'}}>DEAL FINALIZED</strong>}
                {msg.content}
              </div>
            </div>
          );
        })}
      </section>

      {/* RIGHT: Agent Meta & Risk */}
      <aside className={styles.sidebarRight}>
        <h2 className={styles.sectionTitle}>Environment State</h2>
        <div className={styles.inventoryItem}>
          <div className={styles.itemHeader}>TRACING</div>
          <div className={styles.itemSub}>LANGFUSE_CLOUD_ACTIVE</div>
        </div>
        <div className={styles.inventoryItem}>
          <div className={styles.itemHeader}>ORCHESTRATOR</div>
          <div className={styles.itemSub}>LANGGRAPH_CYCLIC_V2</div>
        </div>
        <div className={styles.inventoryItem}>
          <div className={styles.itemHeader}>LLM_PROVIDER</div>
          <div className={styles.itemSub}>GROQ / GPT-OSS-20B</div>
        </div>

        <h2 className={styles.sectionTitle} style={{marginTop: '32px'}}>Scenarios</h2>
        <div className={styles.scenarioList}>
          <button 
            className={styles.scenarioLink}
            onClick={() => setPrompt("Purchase 100 enterprise servers with $500k budget")}
          >
            → Bulk Infrastructure
          </button>
          <button 
            className={styles.scenarioLink}
            onClick={() => setPrompt("I need 50 networking cables fast")}
          >
            → Rapid Procurement
          </button>
        </div>
      </aside>
    </div>
  );
}
