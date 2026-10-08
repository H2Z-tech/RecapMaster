const $=id=>document.getElementById(id);
const setStatus=t=>{$("status").textContent=t};
const setBar=n=>$("bar").style.width=n+"%";

async function run(){
 const url=$("url").value.trim(), file=$("file").files[0];
 if(!url && !file){alert("YouTube link သို့ video file တစ်ခုရွေးပါ။");return}
 $("result").style.display="none"; setBar(10); setStatus("Downloading / reading media...");
 const fd=new FormData();
 fd.append("source_lang",$("source").value);fd.append("target_lang",$("target").value);fd.append("voice",$("voice").value);
 let endpoint="/api/process";
 if(file){endpoint="/api/upload";fd.append("file",file)}else fd.append("url",url);
 try{
   setBar(25);setStatus("Speech-to-text လုပ်နေပါတယ်...");
   const r=await fetch(endpoint,{method:"POST",body:fd});
   const d=await r.json();
   if(!r.ok||!d.ok) throw new Error(d.error||"Processing failed");
   setBar(85);setStatus("Subtitle / recap / voice ပြုလုပ်နေပါတယ်...");
   $("recap").value=d.recap||"";
   $("translation").value=d.translation||"";
   $("srt").value=d.srt||"";
   $("recapDl").href=d.recap_url;$("recapDl").download="recap.txt";
   $("srtDl").href=d.srt_url;$("srtDl").download="subtitles.srt";
   $("txtDl").href=d.translation_url;$("txtDl").download="translation.txt";
   if(d.audio){$("audioDl").href=d.audio;$("audioDl").download="narration.mp3";$("audioDl").style.display="inline-block"}else $("audioDl").style.display="none";
   $("result").style.display="block";setBar(100);setStatus("✅ ပြီးပါပြီ။ Download ခလုတ်ကနေ သိမ်းနိုင်ပါတယ်။");
 }catch(e){setBar(0);setStatus("❌ "+e.message);alert(e.message)}
}
$("process").onclick=run;
