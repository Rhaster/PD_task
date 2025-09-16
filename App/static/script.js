async function sendChat() {
    const prompt = document.getElementById("chat_input").value;
    if (!prompt) return;

    const res = await fetch("/chat", {
        method: "POST",
        body: new URLSearchParams({prompt})
    });
    const data = await res.json();
    
    const chatOutput = document.getElementById("chat_output");
    chatOutput.innerText += "\nYou: " + prompt + "\nBot: " + (data.answer || JSON.stringify(data));
    document.getElementById("chat_input").value = "";
}

async function resetChat() {
    const res = await fetch("/reset_chat", {method: "POST"});
    const data = await res.json();
    document.getElementById("chat_output").innerText = "";
    alert("Chat reset: " + data.status);
}
