// script.js - Enhanced Version with YAML Generation


export const assessmentState = {
  gen: {
    controlState: null,      	// user input to GEN Agent
    rawResponse: null,			// raw response of GEN Agent
    controlGates: null, 		// derivation of response of GEN Agent
	executiveReport: null, 
	analystReport: null,
	remediationReport: null
  },
  domains: {
    identityLifecycle: {
      domainScore: null,
      domainLevel: null,
      questions: {}
    },
    accessGovernance: {
      domainScore: null,
      domainLevel: null,
      questions: {}
    },
    authenticationMFA: {
      domainScore: null,
      domainLevel: null,
      questions: {}
    },
    privilegedAccess: {
      domainScore: null,
      domainLevel: null,
      questions: {}
    },
    monitoringAndLogging: {
      domainScore: null,
      domainLevel: null,
      questions: {}
    }	  
  },
  metadata: {
    assessmentId: crypto.randomUUID(),
    createdAt: new Date().toISOString()
  }  
};

let currentIndex = 0;
let criSectionsArray = [];
let popup = null;

const criAIResponse = {};

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, fetching data...');

	//readExcelFile("CRI_Profile_Final_2025_04_15_Final.xlsx");
	fetch('CRI_Profile_Final_2025_04_15_Final.xlsx')
		.then(response => {
			if (!response.ok) {
				throw new Error('Network response was not ok: ' + response.status);
			}
			return response.arrayBuffer();
		})
		.then(data => {
			const workbook = XLSX.read(data);
			const worksheet = workbook.Sheets["CRI Profile v2.1 Structure"];
			const json = XLSX.utils.sheet_to_json(worksheet, { defval: "", raw: false });
			
			const cleanedJson = json.map(row =>
				Object.fromEntries(
					Object.entries(row).map(([k, v]) => [k.replace(/\r?\n|\r/g, " ").trim(),v])
				)
			);
			initCRI(cleanedJson);
		})
		.catch(error => {
			console.error('Error loading Excel:', error);
		});	
});

function goToNextCri(){
	const dsContainer = document.getElementById("ds-statement-container");
	const block = document.querySelector('.cri-statement-block');
	let index = parseInt(block.dataset.index, 10);
	let newIndex = index + 1;
	dsContainer.innerHTML = "";
	dsContainer.appendChild(criSectionsArray[newIndex]);
	
	const counter = document.getElementById("counter-cri");
	counter.innerHTML = `Question <span class="current-question">` + (newIndex+1) + `</span> of ${criSectionsArray.length}`;
	
	const leftButton = document.querySelector('.nav-left-cri');
	const rightButton = document.querySelector('.nav-right-cri');
	
	if (newIndex === 0) {
		leftButton.disabled = true;
	} else {
		leftButton.disabled = false;
	}
	
	if (newIndex === criSectionsArray.length - 1) {
		rightButton.disabled = true;
	} else {
		rightButton.disabled = false;
	}
	
}

function goToPreviousCri(){
	const dsContainer = document.getElementById("ds-statement-container");
	const block = document.querySelector('.cri-statement-block');
	let index = parseInt(block.dataset.index, 10);
	let newIndex = index - 1;
		
	dsContainer.innerHTML = "";
	dsContainer.appendChild(criSectionsArray[newIndex]);
	
	const counter = document.getElementById("counter-cri");
	counter.innerHTML = `Question <span class="current-question">` + (newIndex+1) + `</span> of ${criSectionsArray.length}`;

	const leftButton = document.querySelector('.nav-left-cri');
	const rightButton = document.querySelector('.nav-right-cri');
	
	if (newIndex === 0) {
		leftButton.disabled = true;
	} else {
		leftButton.disabled = false;
	}
	
	if (newIndex === criSectionsArray.length - 1) {
		rightButton.disabled = true;
	} else {
		rightButton.disabled = false;
	}	
}

function callLLMDecodeClassify(yamlContent){
    const userName = "SunilPK";
    const apiUrl = "https://decode-cri.vercel.app/cri_ds_decodeClassify";	
    // RETURN the fetch promise
    return fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_name: userName,
            cri_ds_statement: yamlContent
        })
    })
    .then(async response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
		const data = await response.json();        
		return data;
    })
    .catch(err => {
        console.error("DS Classification Error:", err);
        return "Error: " + err.message;  // Still return something
    });	
}

function callLLMForDSClassification(yamlContent){
	
    const userName = "SunilPK";
    const apiUrl = "http://localhost:8000/cri_ds_category";	
    // RETURN the fetch promise
    return fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_name: userName,
            cri_ds_statement: yamlContent
        })
    })
    .then(async response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
		const data = await response.json();        
		return data;
    })
    .catch(err => {
        console.error("DS Classification Error:", err);
        return "Error: " + err.message;  // Still return something
    });	
}

function callLLMForDSEvidence(yamlContent){
	const userName = "SunilPK";
    const apiUrl = "http://localhost:8000/cri_ds_evidence";	
    return fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_name: userName,
            cri_ds_statement: yamlContent
        })
    })
    .then(async response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
		const data = await response.json();        
		return data;
    })
    .catch(err => {
        console.error("Connection Error:", err);
        return "Error: " + err.message;  // Still return something
    });	
}

function callLLMForDSInterpretation(yamlContent){
	const userName = "SunilPK";
    const apiUrl = "http://localhost:8000/cri_ds_interpret";	
    return fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_name: userName,
            cri_ds_statement: yamlContent
        })
    })
    .then(async response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
		const data = await response.json();        
		return data;
    })
    .catch(err => {
        console.error("Connection Error:", err);
        return "Error: " + err.message;  // Still return something
    });	
}

function callLLMForDSRegulatorAlignment(yamlContent){
	const userName = "SunilPK";
    const apiUrl = "http://localhost:8000/cri_ds_regulatoralignment";	
    return fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_name: userName,
            cri_ds_statement: yamlContent
        })
    })
    .then(async response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
		const data = await response.json();        
		return data;
    })
    .catch(err => {
        console.error("Connection Error:", err);
        return "Error: " + err.message;  // Still return something
    });		
}

function getRegulatorCoverage(){
	const dsContainer = document.getElementById("ds-statement-container");
	const block = document.querySelector('.cri-statement-block');

	//let smeNarrativeID = `smeNarrative-${block.dataset.profileId}`;
	const data = {
		profileId: block.dataset.profileId,
		outlineId: block.dataset.outlineId,
		index: Number(block.dataset.index),
		profileIdText: block.querySelector('.cri-profile-id').childNodes[0].textContent.trim(),
		outlineText: block.querySelector('.cri-profile-id span').textContent.trim(),
		functionText: block.querySelector('.cri-outline-id').textContent.trim(),
		categoryText: block.querySelector('.cri-category').textContent.trim(),
		diagnosticText: block.querySelector('.cri-diagnostic').textContent.trim(),
		responseGuideText: block.querySelector('.cri-response-guide').textContent.trim()
	};
	
	if (criAIResponse?.[block.dataset.profileId]?.reg_alignment) {
		alert("Data Already Exist, using it");
		let htmlText = convertResponseToHTML(criAIResponse[block.dataset.profileId], block.dataset.profileId, data);
		//popup.document.body.innerHTML = htmlText;
		return;
	}
	
	let category = data.categoryText;
    const funcName = category?.split('/')[0].trim();
    const categoryName = category?.split('/')[1].trim();
	const subCategoryName = category?.split('/')[2].trim();

	
	let yamlContent = "cri_ds_statement:\n"
	yamlContent += "  profile_id: " 			+ `${data.profileId}\n`;
	yamlContent += "  outline_id: " 			+ `${data.outlineId}\n`;
	yamlContent += "  index: " 					+ `${data.index}\n`;
	yamlContent += "  Function: " 				+ `${funcName}\n`;
	yamlContent += "  Category: " 				+ `${categoryName}\n`;
	yamlContent += "  SubCategory: " 			+ `${subCategoryName}\n`;
	yamlContent += `  diagnostic_statement: |\n`;

	// Indent diagnostic text correctly
	const indentedText = data.diagnosticText
		.split('\n')
		.map(line => `    ${line}`)
		.join('\n');

	yamlContent += indentedText + "\n";
	
	yamlContent += `  ResponseGuide: |\n`;
	const rgText = data.responseGuideText
		.split('\n')
		.map(line => `    ${line}`)
		.join('\n');	
	yamlContent += rgText + "\n";
	
	//alert(yamlContent); //Calling AI Agent
	callLLMForDSRegulatorAlignment(yamlContent)
    .then(resp_data => {
		let profileID = `${data.profileId}`;
		
		criAIResponse[profileID] = criAIResponse[profileID] || {};
		criAIResponse[profileID].reg_alignment = resp_data.reg_alignment;
		let htmlText = convertResponseToHTML(criAIResponse[profileID], profileID, data);

		//popup.document.body.innerHTML = htmlText;		
		return "SUCCESS";
    })
    .catch(err => {
		alert(error);
        console.error(err);
    });	
}

function getCRIInterpret(){
	const dsContainer = document.getElementById("ds-statement-container");
	const block = document.querySelector('.cri-statement-block');
	
	
	//let smeNarrativeID = `smeNarrative-${block.dataset.profileId}`;
	const data = {
		profileId: block.dataset.profileId,
		outlineId: block.dataset.outlineId,
		index: Number(block.dataset.index),
		profileIdText: block.querySelector('.cri-profile-id').childNodes[0].textContent.trim(),
		outlineText: block.querySelector('.cri-profile-id span').textContent.trim(),
		functionText: block.querySelector('.cri-outline-id').textContent.trim(),
		categoryText: block.querySelector('.cri-category').textContent.trim(),
		diagnosticText: block.querySelector('.cri-diagnostic').textContent.trim(),
		responseGuideText: block.querySelector('.cri-response-guide').textContent.trim()
	};
	
	if (criAIResponse?.[block.dataset.profileId]?.interpret) {
		alert("Data Already Exist, using it");
		let htmlText = convertResponseToHTML(criAIResponse[block.dataset.profileId], block.dataset.profileId, data);
		//popup.document.body.innerHTML = htmlText;
		return;
	}
	
	let category = data.categoryText;
    const funcName = category?.split('/')[0].trim();
    const categoryName = category?.split('/')[1].trim();
	const subCategoryName = category?.split('/')[2].trim();

	
	let yamlContent = "cri_ds_statement:\n"
	yamlContent += "  profile_id: " 			+ `${data.profileId}\n`;
	yamlContent += "  outline_id: " 			+ `${data.outlineId}\n`;
	yamlContent += "  index: " 					+ `${data.index}\n`;
	yamlContent += "  Function: " 				+ `${funcName}\n`;
	yamlContent += "  Category: " 				+ `${categoryName}\n`;
	yamlContent += "  SubCategory: " 			+ `${subCategoryName}\n`;
	yamlContent += `  diagnostic_statement: |\n`;

	// Indent diagnostic text correctly
	const indentedText = data.diagnosticText
		.split('\n')
		.map(line => `    ${line}`)
		.join('\n');

	yamlContent += indentedText + "\n";
	
	yamlContent += `  ResponseGuide: |\n`;
	const rgText = data.responseGuideText
		.split('\n')
		.map(line => `    ${line}`)
		.join('\n');	
	yamlContent += rgText + "\n";
	
	//alert(yamlContent); //Calling AI Agent
	callLLMForDSInterpretation(yamlContent)
    .then(resp_data => {
		let profileID = `${data.profileId}`;
		
		criAIResponse[profileID] = criAIResponse[profileID] || {};
		criAIResponse[profileID].interpret = resp_data.interpret;
		let htmlText = convertResponseToHTML(criAIResponse[profileID], profileID, data);

		//popup.document.body.innerHTML = htmlText;		
		return "SUCCESS";
		
		
    })
    .catch(err => {
		alert(error);
        console.error(err);
    });
}

function getDecodeAndClassify(){
	const dsContainer = document.getElementById("ds-statement-container");
	const block = document.querySelector('.cri-statement-block');
	
	const data = {
		profileId: block.dataset.profileId,
		outlineId: block.dataset.outlineId,
		index: Number(block.dataset.index),
		profileIdText: block.querySelector('.cri-profile-id').childNodes[0].textContent.trim(),
		outlineText: block.querySelector('.cri-profile-id span').textContent.trim(),
		functionText: block.querySelector('.cri-outline-id').textContent.trim(),
		categoryText: block.querySelector('.cri-category').textContent.trim(),
		diagnosticText: block.querySelector('.cri-diagnostic').textContent.trim(),
		responseGuideText: block.querySelector('.cri-response-guide').textContent.trim()
	};
	/*
	if (criAIResponse?.[block.dataset.profileId]?.classification) {
		alert("Data Already Exist, using it");
		let htmlText = convertResponseToHTML(criAIResponse[block.dataset.profileId], block.dataset.profileId, data);
		//popup.document.body.innerHTML = htmlText;
		return;
	}	*/
	let category = data.categoryText;
    const funcName = category?.split('/')[0].trim();
    const categoryName = category?.split('/')[1].trim();
	const subCategoryName = category?.split('/')[2].trim();

	
	let yamlContent = "cri_ds_statement:\n"
	yamlContent += "  profile_id: " 			+ `${data.profileId}\n`;
	yamlContent += "  outline_id: " 			+ `${data.outlineId}\n`;
	yamlContent += "  index: " 					+ `${data.index}\n`;
	yamlContent += "  Function: " 				+ `${funcName}\n`;
	yamlContent += "  Category: " 				+ `${categoryName}\n`;
	yamlContent += "  SubCategory: " 			+ `${subCategoryName}\n`;
	yamlContent += `  diagnostic_statement: |\n`;

	// Indent diagnostic text correctly
	const indentedText = data.diagnosticText
		.split('\n')
		.map(line => `    ${line}`)
		.join('\n');

	yamlContent += indentedText + "\n";
	
	yamlContent += `  ResponseGuide: |\n`;
	const rgText = data.responseGuideText
		.split('\n')
		.map(line => `    ${line}`)
		.join('\n');	
	yamlContent += rgText + "\n";

	//alert(yamlContent); //Calling AI Agent
	callLLMDecodeClassify(yamlContent)
    .then(resp_data => {
		let profileID = `${data.profileId}`;
				
		criAIResponse[profileID] = criAIResponse[profileID] || {};
		criAIResponse[profileID].cri_interpretation = resp_data.cri_interpretation;
		criAIResponse[profileID].ds_classification = resp_data.ds_classification;
		criAIResponse[profileID].cri_validated_classification = resp_data.cri_validated_classification;
		
		let htmlText = convertResponseToHTML(criAIResponse[profileID], profileID, data);
		
		return "SUCCESS";		
    })
    .catch(err => {
		alert(error);
        console.error(err);
    });
}

function getClassification(){
	const dsContainer = document.getElementById("ds-statement-container");
	const block = document.querySelector('.cri-statement-block');
	
	
	//let smeNarrativeID = `smeNarrative-${block.dataset.profileId}`;
	const data = {
		profileId: block.dataset.profileId,
		outlineId: block.dataset.outlineId,
		index: Number(block.dataset.index),
		profileIdText: block.querySelector('.cri-profile-id').childNodes[0].textContent.trim(),
		outlineText: block.querySelector('.cri-profile-id span').textContent.trim(),
		functionText: block.querySelector('.cri-outline-id').textContent.trim(),
		categoryText: block.querySelector('.cri-category').textContent.trim(),
		diagnosticText: block.querySelector('.cri-diagnostic').textContent.trim(),
		responseGuideText: block.querySelector('.cri-response-guide').textContent.trim()
	};
	/*
	if (criAIResponse?.[block.dataset.profileId]?.classification) {
		alert("Data Already Exist, using it");
		let htmlText = convertResponseToHTML(criAIResponse[block.dataset.profileId], block.dataset.profileId, data);
		//popup.document.body.innerHTML = htmlText;
		return;
	}	*/
	let category = data.categoryText;
    const funcName = category?.split('/')[0].trim();
    const categoryName = category?.split('/')[1].trim();
	const subCategoryName = category?.split('/')[2].trim();

	
	let yamlContent = "cri_ds_statement:\n"
	yamlContent += "  profile_id: " 			+ `${data.profileId}\n`;
	yamlContent += "  outline_id: " 			+ `${data.outlineId}\n`;
	yamlContent += "  index: " 					+ `${data.index}\n`;
	yamlContent += "  Function: " 				+ `${funcName}\n`;
	yamlContent += "  Category: " 				+ `${categoryName}\n`;
	yamlContent += "  SubCategory: " 			+ `${subCategoryName}\n`;
	yamlContent += `  diagnostic_statement: |\n`;

	// Indent diagnostic text correctly
	const indentedText = data.diagnosticText
		.split('\n')
		.map(line => `    ${line}`)
		.join('\n');

	yamlContent += indentedText + "\n";
	
	yamlContent += `  ResponseGuide: |\n`;
	const rgText = data.responseGuideText
		.split('\n')
		.map(line => `    ${line}`)
		.join('\n');	
	yamlContent += rgText + "\n";
	
	//alert(yamlContent); //Calling AI Agent
	callLLMForDSClassification(yamlContent)
    .then(resp_data => {
		let profileID = `${data.profileId}`;
		
		//criAIResponse[profileID] = {
		//	classification: resp_data.Classification,
		//	evidence: resp_data.RequireEvidence
		//};
		
		criAIResponse[profileID] = criAIResponse[profileID] || {};
		criAIResponse[profileID].classification = resp_data.Classification;
		let htmlText = convertResponseToHTML(criAIResponse[profileID], profileID, data);
		
		//let classfyId = `classification-${data.profileId}`;
		//let classification = document.getElementById(classfyId);
		//classification.innerHTML = htmlText;

		//popup.document.body.innerHTML = htmlText;		
		return "SUCCESS";
		
		
    })
    .catch(err => {
		alert(error);
        console.error(err);
    });

}

function getCriDeliveable(){
	const dsContainer = document.getElementById("ds-statement-container");
	const block = document.querySelector('.cri-statement-block');

	//let smeNarrativeID = `smeNarrative-${block.dataset.profileId}`;
	const data = {
		profileId: block.dataset.profileId,
		outlineId: block.dataset.outlineId,
		index: Number(block.dataset.index),
		profileIdText: block.querySelector('.cri-profile-id').childNodes[0].textContent.trim(),
		outlineText: block.querySelector('.cri-profile-id span').textContent.trim(),
		functionText: block.querySelector('.cri-outline-id').textContent.trim(),
		categoryText: block.querySelector('.cri-category').textContent.trim(),
		diagnosticText: block.querySelector('.cri-diagnostic').textContent.trim(),
		responseGuideText: block.querySelector('.cri-response-guide').textContent.trim()
	};
	
	if (criAIResponse?.[block.dataset.profileId]?.evidence) {
		alert("Data Already Exist, using it");
		let htmlText = convertResponseToHTML(criAIResponse[block.dataset.profileId], block.dataset.profileId, data);
		//popup.document.body.innerHTML = htmlText;
		return;
	}	
	
	let category = data.categoryText;
    const funcName = category?.split('/')[0].trim();
    const categoryName = category?.split('/')[1].trim();
	const subCategoryName = category?.split('/')[2].trim();

	
	let yamlContent = "cri_ds_statement:\n"
	yamlContent += "  profile_id: " 			+ `${data.profileId}\n`;
	yamlContent += "  outline_id: " 			+ `${data.outlineId}\n`;
	yamlContent += "  index: " 					+ `${data.index}\n`;
	yamlContent += "  Function: " 				+ `${funcName}\n`;
	yamlContent += "  Category: " 				+ `${categoryName}\n`;
	yamlContent += "  SubCategory: " 			+ `${subCategoryName}\n`;
	yamlContent += `  diagnostic_statement: |\n`;

	// Indent diagnostic text correctly
	const indentedText = data.diagnosticText
		.split('\n')
		.map(line => `    ${line}`)
		.join('\n');

	yamlContent += indentedText + "\n";
	
	yamlContent += `  ResponseGuide: |\n`;
	const rgText = data.responseGuideText
		.split('\n')
		.map(line => `    ${line}`)
		.join('\n');	
	yamlContent += rgText + "\n";
	
	//alert(yamlContent); //Calling AI Agent
	callLLMForDSEvidence(yamlContent)
    .then(resp_data => {
		let profileID = `${data.profileId}`;
				
		criAIResponse[profileID] = criAIResponse[profileID] || {};
		criAIResponse[profileID].evidence = resp_data.RequireEvidence;	
	
		let htmlText = convertResponseToHTML(criAIResponse[profileID], profileID, data);
		
		//popup.document.body.innerHTML = htmlText;		
		return "SUCCESS";
		
		
    })
    .catch(err => {
        console.error(err);
    });	
}


function convertResponseToHTML(criResponse, profileID, data) {
    popup.document.close();
    popup.document.open();

    // ── Data extraction ───────────────────────────────────────────────────────
    const [prefix, dsText]  = (data.diagnosticText).split(':');
    const interp            = criResponse.cri_interpretation.understanding;
    const cc                = interp.control_characteristics;
    const classif           = criResponse.ds_classification.Classification;
    const validated         = criResponse.cri_validated_classification;

    // ── Helpers ───────────────────────────────────────────────────────────────
    const badge = (val) =>
        `<span class="badge ${val ? 'badge-yes' : 'badge-no'}">${val ? '✔ Yes' : '✘ No'}</span>`;

    const pill = (label, value) =>
        `<span class="pill"><b>${label}:</b> ${value}</span>`;

    // ── Section 1: CRI Interpretation ────────────────────────────────────────
    const capabilitiesHTML = interp.key_capabilities
        .map(i => `<li>${i.capability}</li>`).join('');

    const focusHTML = interp.assessor_focus
        .map(i => `<li>${i.focus_area}</li>`).join('');

    const pillsHTML = [
        ["Type", cc.control_type],
        ["Mode", cc.execution_mode],
        ["Frequency", cc.frequency],
        ["Layer", cc.implementation_layer],
        ["Scope", cc.scope]
    ].map(([l, v]) => pill(l, v)).join('');

    const interpHTML = `
    <div class="card">
        <div class="card-title">📋 CRI Interpretation</div>
        <div class="two-col">
            <div class="col">
                <div class="label">Explanation</div>
                <p class="text-sm">${interp.simple_explanation}</p>
                <div class="label" style="margin-top:10px">Regulatory Context</div>
                <p class="text-xs italic">${interp.regulatory_context}</p>
                <div class="label" style="margin-top:10px">Control Characteristics</div>
                <div class="pills">${pillsHTML}</div>
            </div>
            <div class="col">
                <div class="label">Key Capabilities</div>
                <ul>${capabilitiesHTML}</ul>
                <div class="label" style="margin-top:8px">Assessor Focus Areas</div>
                <ul>${focusHTML}</ul>
            </div>
        </div>
    </div>`;

    // ── Section 2: DS Classification (left) + Validated (right) ──────────────
    // No Reason column in validated table — user sees the result, not the process
    const classifRows = Object.entries(classif)
        .map(([key, { value, justification }], i) => `
        <tr class="${i % 2 === 0 ? '' : 'alt'}">
            <td class="cat">${key}</td>
            <td class="val-cell">${badge(value)}</td>
            <td class="just">${justification}</td>
        </tr>`).join('');

    const flagsHTML = Object.entries(validated.validated_classification)
        .map(([key, value], i) => `
        <tr class="${i % 2 === 0 ? '' : 'alt'}">
            <td class="cat">${key}</td>
            <td class="val-cell">${badge(value)}</td>
        </tr>`).join('');

    const splitHTML = `
    <div class="card split-card">
        <div class="split-left">
            <div class="card-title">🏷️ DS Classification</div>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th style="width:62px;text-align:center">Value</th>
                        <th>Justification</th>
                    </tr>
                </thead>
                <tbody>${classifRows}</tbody>
            </table>
        </div>
        <div class="split-divider"></div>
        <div class="split-right">
            <div class="card-title">✅ Validated Classification</div>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th style="width:62px;text-align:center">Value</th>
                    </tr>
                </thead>
                <tbody>${flagsHTML}</tbody>
            </table>
        </div>
    </div>`;

    // ── Section 3: Classification Notes ──────────────────────────────────────
    // Show only when Prompt 2 value differs from validated value
    // Plain English — no pipeline language, no rule names
    const prompt2Values = Object.fromEntries(
        Object.entries(classif).map(([k, v]) => [k, v.value])
    );

    const validatedValues = validated.validated_classification;

    const changedDimensions = Object.entries(validatedValues)
        .filter(([dim, val]) => prompt2Values[dim] !== val);

    const dimensionNotes = {
        GovernanceIntent:     {
            toTrue:  "GovernanceIntent confirmed — this control establishes policy, accountability, or organizational direction.",
            toFalse: "GovernanceIntent confirmed as not applicable — this control does not establish governance direction."
        },
        TechnicalEnforcement: {
            toTrue:  "TechnicalEnforcement confirmed — this control is enforced through systems or technical mechanisms.",
            toFalse: "TechnicalEnforcement confirmed as not applicable — this control does not enforce through technical mechanisms."
        },
        Monitoring:           {
            toTrue:  "Monitoring confirmed — this control involves detection, logging, or visibility into system state.",
            toFalse: "Monitoring confirmed as not applicable — this control does not observe or detect system state."
        },
        Automation:           {
            toTrue:  "Automation confirmed — this control executes automatically without manual intervention.",
            toFalse: "Automation confirmed as not applicable — this control requires human execution."
        },
        Lifecycle:            {
            toTrue:  "Lifecycle confirmed — this control requires ongoing management, periodic reviews, or recurring activity.",
            toFalse: "Lifecycle confirmed as not applicable — this control is not a recurring or ongoing obligation."
        },
        StrategicIntent:      {
            toTrue:  "StrategicIntent confirmed — this control represents high-level direction with no operational mechanics.",
            toFalse: "StrategicIntent confirmed as not applicable — this control has active operational dimensions."
        }
    };

    const classificationNotesHTML = changedDimensions.length > 0
        ? `
    <div class="card">
        <div class="card-title">📝 Classification Notes</div>
        <table>
            <thead>
                <tr>
                    <th style="width:160px">Dimension</th>
                    <th style="width:62px;text-align:center">Final Value</th>
                    <th>Note</th>
                </tr>
            </thead>
            <tbody>
                ${changedDimensions.map(([dim, val], i) => `
                <tr class="${i % 2 === 0 ? '' : 'alt'}">
                    <td class="cat">${dim}</td>
                    <td class="val-cell">${badge(val)}</td>
                    <td class="just">${dimensionNotes[dim]
                        ? (val ? dimensionNotes[dim].toTrue : dimensionNotes[dim].toFalse)
                        : (val ? `${dim} confirmed TRUE.` : `${dim} confirmed FALSE.`)
                    }</td>
                </tr>`).join('')}
            </tbody>
        </table>
    </div>`
        : '';

    // ── Section 4: Examination Considerations (Tensions) ─────────────────────
    // Only shown when tensions exist — renamed from Tensions for user clarity
    const tensionsRowsHTML = (validated.tensions && validated.tensions.length > 0)
        ? validated.tensions.map((t, i) => `
            <tr class="${i % 2 === 0 ? '' : 'alt'}">
                <td class="cat">${t.dimension}</td>
                <td class="just">${t.description}</td>
                <td class="just">${t.exam_implication}</td>
                <td class="just">${t.recommendation}</td>
            </tr>`).join('')
        : null;

    const examinationConsiderationsHTML = tensionsRowsHTML
        ? `
    <div class="card">
        <div class="card-title">⚡ Assessment Considerations</div>
        <table>
            <thead>
                <tr>
                    <th style="width:130px">Dimension</th>
                    <th>Description</th>
                    <th>What Examiner Will Probe</th>
                    <th>Recommendation</th>
                </tr>
            </thead>
            <tbody>${tensionsRowsHTML}</tbody>
        </table>
    </div>`
        : '';

    // ── Section 5: Evidence to Prepare (Exam Guidance) ───────────────────────
    // Renamed from Exam Guidance — more actionable language for user
    const examRowsHTML = (validated.exam_guidance && validated.exam_guidance.length > 0)
        ? validated.exam_guidance.map((e, i) => `
            <tr class="${i % 2 === 0 ? '' : 'alt'}">
                <td class="cat">${e.dimension}</td>
                <td class="just">${e.evidence_required}</td>
                <td class="just">${e.examiner_likely_to_probe}</td>
            </tr>`).join('')
        : null;

    const evidenceToPrepareHTML = examRowsHTML
        ? `
    <div class="card">
        <div class="card-title">📌 Evidence to Prepare</div>
        <table>
            <thead>
                <tr>
                    <th style="width:130px">Dimension</th>
                    <th>Evidence Required</th>
                    <th>Examiner Likely to Probe</th>
                </tr>
            </thead>
            <tbody>${examRowsHTML}</tbody>
        </table>
    </div>`
        : '';

    // ── Section 6: Examination Status (Validation Summary) ───────────────────
    // Simplified — only confidence and readiness shown to user
    const vs = validated.validation_summary;

    const confidenceConfig = {
        high:   { cls: 'conf-high',   label: 'HIGH' },
        medium: { cls: 'conf-medium', label: 'MEDIUM' },
        low:    { cls: 'conf-low',    label: 'LOW' }
    };

	var examinationStatusHTML = "";
	if(vs!=null){
    	const conf = confidenceConfig[vs.overall_confidence] || confidenceConfig.medium;
		
    	const readinessMessage = vs.examination_ready
        	? `<span class="readiness-ready">✔ This control is assessment-ready</span>`
        	: `<span class="readiness-review">⚠ This control requires review before assessment</span>`;

    	examinationStatusHTML = `
    	<div class="card">
        	<div class="card-title">📊 Assessment Readiness Status</div>
        	<div class="status-grid">
            	<div class="status-item">
                	<div class="label">Classification Confidence</div>
                	<div class="status-value">
                    	<span class="conf-badge ${conf.cls}">${conf.label}</span>
                	</div>
            	</div>
            	<div class="status-item status-readiness">
                	<div class="label">Assessment Readiness</div>
                	<div class="status-value">${readinessMessage}</div>
            	</div>
        	</div>
    	</div>`;
	}
    // ── Assemble body HTML ────────────────────────────────────────────────────
    const bodyHTML = `
    <div class="top-bar">
        <div class="top-left">
            <span class="profile-id">Profile ${profileID}</span>
            <span class="ds-text">${doColor(dsText)}</span>
        </div>
        <button class="pdf-btn" onclick="savePDF()">Save as PDF</button>
    </div>

    <div class="context-bar">
        <span><b>Sector:</b> ${doColor(data.sectorText)}</span>
        <span><b>Size:</b> ${doColor(data.orgSizeText)}</span>
        <span><b>Location(s):</b> ${doColor(data.geographyText)}</span>
        <span><b>Regulations:</b> ${doColor(data.regulatoryText)}</span>
    </div>

    ${interpHTML}
    ${splitHTML}
    ${classificationNotesHTML}
    ${examinationConsiderationsHTML}
    ${evidenceToPrepareHTML}
    ${examinationStatusHTML}`;

    // ── Full document ─────────────────────────────────────────────────────────
    popup.document.write(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CRI Response — Profile ${profileID}</title>
<style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 13px;
        background: #eef3f9;
        color: #2c3e50;
        padding: 16px 24px;
        line-height: 1.5;
    }

    /* ── Top bar ── */
    .top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .top-left { display: flex; align-items: baseline; gap: 12px; }
    .profile-id { font-size: 17px; font-weight: 700; color: #1f4e79; }
    .ds-text { font-size: 12px; color: #555; }

    /* ── PDF button ── */
    .pdf-btn {
        display: inline-flex; align-items: center; gap: 5px;
        background: #1f4e79; color: #fff; border: none;
        padding: 6px 14px; border-radius: 5px; font-size: 12px;
        cursor: pointer; font-family: inherit;
    }
    .pdf-btn:hover { background: #163d5e; }

    /* ── Context bar ── */
    .context-bar {
        display: flex; flex-wrap: wrap; gap: 4px 18px;
        font-size: 12px; color: #444;
        background: #fff; border-radius: 6px;
        padding: 7px 14px; margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.07);
        border-left: 4px solid #1f4e79;
    }

    /* ── Card ── */
    .card {
        background: #fff; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.09);
    }
    .card-title {
        font-size: 12px; font-weight: 700;
        color: #1f4e79; text-transform: uppercase;
        letter-spacing: 0.4px;
        border-bottom: 2px solid #cfe2f3;
        padding-bottom: 5px; margin-bottom: 10px;
    }

    /* ── Two-column (Interpretation) ── */
    .two-col { display: flex; gap: 20px; }
    .col { flex: 1; min-width: 0; }

    /* ── Labels ── */
    .label {
        font-size: 10px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.6px;
        color: #1565c0; margin-bottom: 4px;
    }

    /* ── Text helpers ── */
    .text-sm { font-size: 12px; color: #444; }
    .italic { font-style: italic; color: #666; font-size: 11px; }

    /* ── Pills ── */
    .pills { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 4px; }
    .pill {
        padding: 2px 9px; border-radius: 20px; font-size: 11px;
        background: #e3f2fd; color: #1565c0; border: 1px solid #90caf9;
    }

    /* ── Lists ── */
    ul { margin: 4px 0 6px 15px; }
    li { margin-bottom: 3px; font-size: 12px; color: #444; }

    /* ── Split card ── */
    .split-card {
        display: flex;
        padding: 0;
        overflow: hidden;
    }
    .split-left {
        width: 55%;
        padding: 12px 16px;
        min-width: 0;
    }
    .split-right {
        width: 45%;
        padding: 12px 16px;
        min-width: 0;
        background: #fafcff;
    }
    .split-divider {
        width: 1px;
        background: #cfe2f3;
        flex-shrink: 0;
        margin: 10px 0;
    }

    /* ── Table ── */
    table { width: 100%; border-collapse: collapse; font-size: 11.5px; }
    th {
        background: #e8eaf6; text-align: left;
        padding: 5px 8px; border: 1px solid #ddd;
        font-size: 11px; font-weight: 700;
    }
    td { padding: 5px 8px; border: 1px solid #e8e8e8; vertical-align: top; }
    tr.alt td { background: #f7f9fd; }
    .cat { font-weight: 600; white-space: nowrap; color: #1f4e79; }
    .val-cell { text-align: center; }
    .just { color: #555; font-size: 11px; }

    /* ── Badges ── */
    .badge {
        display: inline-block; padding: 2px 7px;
        border-radius: 10px; font-size: 10.5px;
        font-weight: 700; color: #fff;
    }
    .badge-yes { background: #2e7d32; }
    .badge-no  { background: #b71c1c; }

    /* ── Confidence badge ── */
    .conf-badge {
        display: inline-block; padding: 3px 14px;
        border-radius: 10px; font-size: 11px;
        font-weight: 700; letter-spacing: 0.5px;
    }
    .conf-high   { background: #e8f5e9; color: #2e7d32;
                   border: 1px solid #a5d6a7; }
    .conf-medium { background: #fff8e1; color: #f57f17;
                   border: 1px solid #ffe082; }
    .conf-low    { background: #ffebee; color: #b71c1c;
                   border: 1px solid #ef9a9a; }

    /* ── Examination status ── */
    .status-grid {
        display: grid;
        grid-template-columns: 200px 1fr;
        gap: 12px;
        align-items: center;
    }
    .status-item {
        background: #f5f8ff;
        border: 1px solid #dce8f5;
        border-radius: 6px;
        padding: 10px 14px;
    }
    .status-readiness { grid-column: span 1; }
    .status-value { margin-top: 6px; }

    .readiness-ready {
        font-size: 13px; font-weight: 700;
        color: #2e7d32;
    }
    .readiness-review {
        font-size: 13px; font-weight: 700;
        color: #f57f17;
    }

    /* ── Print ── */
    @media print {
        body { background: #fff; padding: 8px; }
        .pdf-btn { display: none !important; }
        .card, .context-bar { box-shadow: none; border: 1px solid #ddd; }
        .split-card { border: 1px solid #ddd; }
    }
</style>
</head>
<body>

${bodyHTML}

<script>
function savePDF() {
    const btn = document.querySelector('.pdf-btn');
    btn.style.display = 'none';
    window.print();
    setTimeout(() => btn.style.display = 'inline-flex', 500);
}
<\/script>

</body>
</html>`);

    return bodyHTML;
}



function doColor(txt){
	let retText = "";
	if(txt === false || String(txt).trim() === "false"){
		retText = "<text style=\"color: red;\">" + txt + "</text>";
	}
	else{
		retText = "<text style=\"color: blue;\">" + txt + "</text>";
	}
	return retText;
}

function initCRI(criJson) {
    const criContainer = document.getElementById('cri-final-content');
    
    if (!criContainer) {
        alert('Cannot find questions-container element!');
        return;
    }
	const dsRows = criJson.filter(row => row.Level?.trim().toUpperCase() === "DS");
    // Clear any existing content
    criContainer.innerHTML = '';
	
	const criSection = document.createElement('div');
    criSection.className = 'domain-cri-section';
    criSection.id = "domain-cri";

    const header = document.createElement('h3');
    header.innerHTML = "CRI Diagnostic Statement";

    // Domain description
    const description = document.createElement('p');
    description.textContent = "";
	description.style = "font-size: 1rem; color: var(--text-light);";
	
    // Create navigation container
    const navContainer = document.createElement('div');
    navContainer.className = 'question-cri-container';
    
    // Create left navigation button
    const leftButton = document.createElement('button');
    leftButton.className = 'nav-button-cri nav-left-cri';
    leftButton.innerHTML = '&larr; Previous';
    leftButton.setAttribute('data-domain-cri', "CRI");
    leftButton.setAttribute('data-direction-cri', 'prev');
	// Add click event
	leftButton.addEventListener('click', function () {
		goToPreviousCri();
	});	
    leftButton.disabled = true;
    // Create right navigation button
    const rightButton = document.createElement('button');
    rightButton.className = 'nav-button-cri nav-right-cri';
    rightButton.innerHTML = 'Next &rarr;';
    rightButton.setAttribute('data-domain-cri', "CRI");
    rightButton.setAttribute('data-direction-cri', 'next');

	// Add click event
	rightButton.addEventListener('click', function () {
		goToNextCri();
	});	
    
    // Create question counter
    const counter = document.createElement('div');
    counter.className = 'question-counter';
    counter.id = "counter-cri";
    counter.innerHTML = `Question <span class="current-question">1</span> of ${dsRows.length}`;	
	
    navContainer.appendChild(leftButton);
    navContainer.appendChild(counter);
    navContainer.appendChild(rightButton);	
	
	
    criSection.appendChild(header);
    criSection.appendChild(description);
	criSection.appendChild(navContainer);
	criContainer.appendChild(criSection);
	
    const dsContainer = document.createElement('div');
    dsContainer.className = 'ds-container';
    dsContainer.id = "ds-statement-container";	

	criSectionsArray = generateCRIHtmlNew(criJson);
	
	dsContainer.appendChild(criSectionsArray[0]);

	criContainer.appendChild(dsContainer);

    // Create left navigation button
	const operationSection = document.createElement('div');

	
    const decodeClassifyValidateButton = document.createElement('button');
    decodeClassifyValidateButton.className = 'nav-button-cri btn-cri-classification';
    decodeClassifyValidateButton.innerHTML = 'Decode & Classify';
	// Add click event
	decodeClassifyValidateButton.addEventListener('click', function () {
		popup = window.open("", "popupWindow", "width=1500,height=600");
		popup.document.write("<html><body><p>Calling AI Agent...waiting for response...</p></body></html>");		
		getDecodeAndClassify();
	});	
	operationSection.appendChild(decodeClassifyValidateButton);

	
    //const classificationButton = document.createElement('button');
    //classificationButton.className = 'nav-button-cri btn-cri-classification';
    //classificationButton.innerHTML = 'CRI Classification';
	// Add click event
	//classificationButton.addEventListener('click', async function () {
	//	popup = window.open("", "popupWindow", "width=1500,height=600");
	//	popup.document.write("<html><body><p>Calling AI Agent...waiting for response...</p></body></html>");
	//	let response = getClassification();
	//});	
	//operationSection.appendChild(classificationButton);


    //const criDeliverableButton = document.createElement('button');
    //criDeliverableButton.className = 'nav-button-cri btn-cri-classification';
    //criDeliverableButton.innerHTML = 'Deliverables';
	// Add click event
	//criDeliverableButton.addEventListener('click', function () {
	//	popup = window.open("", "popupWindow", "width=1500,height=600");
	//	popup.document.write("<p>Calling AI Agent...waiting for response...</p>");
	//	getCriDeliveable();
	//});	
	//operationSection.appendChild(criDeliverableButton);


    //const criInterpreterButton = document.createElement('button');
    //criInterpreterButton.className = 'nav-button-cri btn-cri-classification';
    //criInterpreterButton.innerHTML = 'DS Interpreter';
	// Add click event
	//criInterpreterButton.addEventListener('click', function () {
	//	popup = window.open("", "popupWindow", "width=1500,height=600");
	//	popup.document.write("<p>Calling AI Agent...waiting for response...</p>");		
	//	getCRIInterpret();
	//});	
	//operationSection.appendChild(criInterpreterButton);

    //const regulatoryAlignmentButton = document.createElement('button');
    //regulatoryAlignmentButton.className = 'nav-button-cri btn-cri-classification';
    //regulatoryAlignmentButton.innerHTML = 'Regulatory Coverage & Gap Detection';
	// Add click event
	//regulatoryAlignmentButton.addEventListener('click', function () {
	//	popup = window.open("", "popupWindow", "width=1500,height=600");
	//	popup.document.write("<p>Calling AI Agent...waiting for response...</p>");
	//	getRegulatorCoverage();
	//});	
	//operationSection.appendChild(regulatoryAlignmentButton);
	
	criContainer.appendChild(operationSection);
    //updateCounter();
}

function generateCRIHtmlNew(criJson) {
	const dsRows = criJson.filter(row => row.Level?.trim().toUpperCase() === "DS");
		
    const dsSections = dsRows.map((row, index) => {
        // Create main statement container
        const statement = document.createElement('div');
		
        statement.className = 'cri-statement-block';
        statement.dataset.profileId = row["Profile Id"];
        statement.dataset.outlineId = row["Outline Id"];
		statement.dataset.index=index;

        // Header
        const header = document.createElement('div');
        header.className = 'cri-header';

        const profileIdDiv = document.createElement('div');
        profileIdDiv.className = 'cri-profile-id';
        profileIdDiv.innerHTML = `${row["Profile Id"]} <span>Outline ID: ${row["Outline Id"]}</span>`;

        const outlineDiv = document.createElement('div');
        outlineDiv.className = 'cri-outline-id';
        const funcName = row["CRI Profile Function /  Category / Subcategory"]?.split('/')[0].trim();
        outlineDiv.textContent = `Function: ${funcName}`;

        header.appendChild(profileIdDiv);
        header.appendChild(outlineDiv);
        statement.appendChild(header);

        // Category Section
        const categorySection = document.createElement('div');
        categorySection.className = 'cri-category-section';

        const catH4 = document.createElement('h4');
        catH4.textContent = 'Function / Category / Subcategory';
        const catP = document.createElement('p');
        catP.className = 'cri-category';
        catP.textContent = row["CRI Profile Function /  Category / Subcategory"];

		categorySection.appendChild(catH4);
        categorySection.appendChild(catP);
        statement.appendChild(categorySection);

        // Diagnostic Statement
        const diagSection = document.createElement('div');
        diagSection.className = 'cri-statement-section';

        const diagH4 = document.createElement('h4');
        diagH4.textContent = 'Diagnostic Statement';
        const diagP = document.createElement('p');
        diagP.className = 'cri-diagnostic';
        diagP.textContent = row["CRI Profile v2.1 Diagnostic Statement"];

        diagSection.appendChild(diagH4);
        diagSection.appendChild(diagP);
        statement.appendChild(diagSection);
		
		//Response guide
		const responseGuide = document.createElement('div');
		responseGuide.className = 'cri-responseguide-section';
		const respGH4 = document.createElement('h4');
		respGH4.textContent = "Response Guide";
		const respGHP = document.createElement('p');
		respGHP.className = 'cri-response-guide';
		respGHP.textContent = row["Response Guidance"];
		
        responseGuide.appendChild(respGH4);
        responseGuide.appendChild(respGHP);
        statement.appendChild(responseGuide);		

		//EEE
		//const eeeSection = document.createElement('div');
		//responseGuide.className = 'cri-eee-section';
		//const eeeGH4 = document.createElement('h4');
		//eeeGH4.textContent = "Example of Effective Evidence";
		//const eeeGHP = document.createElement('p');
		//eeeGHP.className = 'cri-eee-guide';
		//eeeGHP.textContent = row["EEE"];
		
        //responseGuide.appendChild(eeeGH4);
        //responseGuide.appendChild(eeeGHP);
        //statement.appendChild(eeeSection);		

        // FIN section
        //const finSection = document.createElement('div');
        //finSection.className = 'cri-fin-section';
        //const finH4 = document.createElement('h4');
        //finH4.textContent = 'Financial Services References';
		//const finP = document.createElement('p');
		//finP.className = 'cri-financial';
		//finP.textContent = row["Financial Services Mapping References"];
		
        //finSection.appendChild(finH4);
		//finSection.appendChild(finP);
        //statement.appendChild(finSection);	
		
		//const classification = document.createElement('div');
		//classification.className = "cri-classification-section";
		//classification.id = `classification-${row["Profile Id"]}`;
		//classification.textContent = "";
		//classification.style = "font-size: 1rem;";
		//statement.appendChild(classification);
		
		//const evidenceList = document.createElement('div');
		//evidenceList.className = "cri-evidence-section";
		//evidenceList.id = `evidenceList-${row["Profile Id"]}`;
		//evidenceList.textContent = "";
		//evidenceList.style = "font-size: 1rem;";
		//statement.appendChild(evidenceList);		
		
        return statement;
    });	
    return dsSections;
}

function updateCounter() {
    const counter = document.querySelector('#cri-counter .current-cri');
    if (counter) counter.textContent = currentIndex + 1;
}

function buildGenState(allAnswers) {
  function getAnswerTruthValue(questionId) {
    const answer = allAnswers.get(questionId);
    return answer && answer.answer === "true";
  }

  const genState = {};

  for (let i = 1; i <= 18; i++) {
    genState[`Q${i}`] = getAnswerTruthValue(`GEN-Q${i}`);
  }

  return genState;
}

function generateGeneralQuestionsHTML(domains) {
    console.log('Generating HTML for domains:', domains);
    
    // Get the container where questions should go
    const questionsContainer = document.getElementById('questions-container');
    
    if (!questionsContainer) {
        console.error('Cannot find questions-container element!');
        return;
    }
    
    // Clear any existing content
    questionsContainer.innerHTML = '';
    
    // Create a container for all domains
    const allDomainsContainer = document.createElement('div');
    allDomainsContainer.className = 'all-domains-container';
    
    // Generate HTML for each domain
    domains.forEach(domain => {
        const domainSection = createGeneralDomainSection(domain);
        allDomainsContainer.appendChild(domainSection);
    });
    
    questionsContainer.appendChild(allDomainsContainer);
    console.log('Questions HTML generated successfully');
}

function createGeneralDomainSection(domain) {
    const section = document.createElement('div');
	//section.style = "width:50%";
    section.className = 'domain-section';
    section.id = `domain-${domain.id}`;
    
    // Domain header
    const header = document.createElement('h3');
    header.innerHTML = `${domain.id}. ${domain.name}`;
    
    // Domain description
    const description = document.createElement('p');
    description.textContent = domain.description;
	description.style = "font-size: 1rem; color: var(--text-light);";
    
    // Create navigation container
    const navContainer = document.createElement('div');
    navContainer.className = 'question-nav-container';
    
    // Create left navigation button
    const leftButton = document.createElement('button');
    leftButton.className = 'nav-button nav-left';
    leftButton.innerHTML = '&larr; Previous';
    leftButton.setAttribute('data-domain', domain.id);
    leftButton.setAttribute('data-direction', 'prev');
    
    // Create right navigation button
    const rightButton = document.createElement('button');
    rightButton.className = 'nav-button nav-right';
    rightButton.innerHTML = 'Next &rarr;';
    rightButton.setAttribute('data-domain', domain.id);
    rightButton.setAttribute('data-direction', 'next');
    
    // Create question counter
    const counter = document.createElement('div');
    counter.className = 'question-counter';
    counter.id = `counter-${domain.id}`;
    counter.innerHTML = `Question <span class="current-question">1</span> of ${domain.questions.length}`;
    
    // Create questions container (initially hidden)
    const questionsContainer = document.createElement('div');
    questionsContainer.className = 'questions-container';
    questionsContainer.id = `questions-${domain.id}`;
    questionsContainer.style.display = 'block'; // Show first question by default
    
    // Create individual question containers
    domain.questions.forEach((question, index) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question-block';
        questionDiv.id = `question-${domain.id}-${question.id}`;
        questionDiv.setAttribute('data-question-id', question.id);
        questionDiv.setAttribute('data-weight', question.weight);
        questionDiv.setAttribute('data-domain-name', domain.name);
        questionDiv.setAttribute('data-index', index);
        
        // Hide all questions except the first one
        if (index > 0) {
            questionDiv.style.display = 'none';
        }
        
        // Create question content
		const domainName = domain.name;
		if(domainName.includes("General") == true){
			questionDiv.innerHTML = createGeneralQuestionContent(question, domain);
		}		
        questionsContainer.appendChild(questionDiv);
    });
    
    // Assemble navigation
    navContainer.appendChild(leftButton);
    navContainer.appendChild(counter);
    navContainer.appendChild(rightButton);
    
    section.appendChild(header);
    section.appendChild(description);
    section.appendChild(navContainer);
    section.appendChild(questionsContainer);
	const dName = domain.name;
	if(dName.includes("General") == true){
		section.innerHTML += `
			<div class="global-actions">
			  <button type="button" class="generate-general-yaml-btn" id="generateAllGenAnsBtn" disabled>
				See Answer
			  </button>
			</div>
		`;
	}
    
    return section;

}

function createGeneralQuestionContent(question, domain) {
    // Create the first 3 options (Levels 1-3)
    const optionsRow1 = question.options.slice(0, 3).map(option => `
        <label class="tile-radio">
            <input type="radio" name="${question.id}" value="${option.value}" 
                   data-question-id="${question.id}" data-domain="${domain.id}"
                   class="general-question-radio" required>
            <span>${option.description}</span>
        </label>
    `).join('');
    
    return `
		<div class="question-text" style="font-size: 1rem; color: var(--text-light);">
			<strong>${question.text}</strong>
		</div>
		<div class="question-clarification" style="font-size: 1rem; color: var(--text-light);">
			<i>${question.clarification}</i>
		</div> 
		<div class="tile-row">
			${optionsRow1}
		</div>
    `;
}

function initializeNavigation() {
    // Add event listeners to all navigation buttons
    const navButtons = document.querySelectorAll('.nav-button');
    navButtons.forEach(button => {
        button.addEventListener('click', function() {
            const domainId = this.getAttribute('data-domain');
            const direction = this.getAttribute('data-direction');
            navigateQuestion(domainId, direction);
        });
    });
    
    // Add styles for navigation
    const style = document.createElement('style');
    style.textContent = `
        .question-nav-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 20px 0;
            padding: 10px;
            background-color: #f5f5f5;
            border-radius: 8px;
        }
        
        .nav-button {
            padding: 8px 16px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.2s;
        }
        
        .nav-button:hover {
            background-color: #0056b3;
        }
        
        .nav-button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        
        .question-counter {
            font-weight: bold;
            color: #333;
        }
        
        .questions-container {
            margin-top: 20px;
        }
        
        .question-full-block {
            padding: 10px;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        /* Update existing styles for new layout */
        .question-block {
            display: none;
        }
        
        .question-block:first-child {
            display: block;
        }
    `;
    document.head.appendChild(style);
    
    // Initialize button states
    updateNavButtonStates();
}

function navigateQuestion(domainId, direction) {
	
    const questionsContainer = document.getElementById(`questions-${domainId}`);
    const questions = questionsContainer.querySelectorAll('.question-block');
    const counter = document.getElementById(`counter-${domainId}`);
    
    // Find current visible question
    let currentIndex = -1;
    questions.forEach((question, index) => {
        if (question.style.display !== 'none') {
            currentIndex = index;
        }
    });
    // Calculate new index
    let newIndex = currentIndex;
    if (direction === 'next' && currentIndex < questions.length - 1) {
        newIndex = currentIndex + 1;
    } else if (direction === 'prev' && currentIndex > 0) {
        newIndex = currentIndex - 1;
    }
    // Update visibility
    if (newIndex !== currentIndex) {
        questions[currentIndex].style.display = 'none';
        questions[newIndex].style.display = 'block';
        
        // Update counter
        counter.querySelector('.current-question').textContent = newIndex + 1;
        
        // Update button states
        updateNavButtonStates();
        
        // Scroll to the question, this is not required at this point
        //questions[newIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
	else if(currentIndex == -1){
		questions[0].style.display = 'block';
		newIndex = 0;
		counter.querySelector('.current-question').textContent = newIndex + 1;
		currentIndex = 1;
	}
}

function updateNavButtonStates() {
    // Update all navigation buttons based on current question positions
    const navContainers = document.querySelectorAll('.question-nav-container');
    
    navContainers.forEach(container => {
        const domainId = container.querySelector('.nav-button').getAttribute('data-domain');
        const questionsContainer = document.getElementById(`questions-${domainId}`);
        const questions = questionsContainer.querySelectorAll('.question-block');
        const leftButton = container.querySelector('.nav-left');
        const rightButton = container.querySelector('.nav-right');
        
        // Find current visible question
        let currentIndex = -1;
        questions.forEach((question, index) => {
            if (question.style.display !== 'none') {
                currentIndex = index;
            }
        });
        
        // Update button states
        if (currentIndex === 0) {
            leftButton.disabled = true;
        } else {
            leftButton.disabled = false;
        }
        
        if (currentIndex === questions.length - 1) {
            rightButton.disabled = true;
        } else {
            rightButton.disabled = false;
        }
    });
}

const allAnswers = new Map();
const totalQuestions = 18;

// Function to check if all questions are answered
function checkAllQuestionsAnswered() {
	if(allAnswers.size > 0)
		return true;
	else
		return false;
    //return allAnswers.size === totalQuestions;
}

async function evaluateGeneralQuestionConditions(allAnswers, yamlPath) {
  // 1. Build normalized GEN state
  const genState = buildGenState(allAnswers);

  console.log("GEN STATE:", genState);

  // 2. Execute YAML policy engine
  const policyResult = await executePolicyEngine(genState, 'banking_V0.1.yaml');

  console.log("POLICY RESULT:", policyResult);

  return policyResult;
}

async function generateFinalGenResult() {
  if (allAnswers.size < totalQuestions) {
    alert("Please answer all 18 questions before generating results.");
    return;
  }

  const generateAllBtn = document.getElementById("generateAllGenAnsBtn");
  generateAllBtn.textContent = "Evaluating...";
  generateAllBtn.disabled = true;

  try {
    // 1. Build GEN state
    const genState = buildGenState(allAnswers);
    console.log("GEN STATE:", genState);

    // 2. Run policy engine
    //const governanceResult = await executePolicyEngine(genState, 'banking_V0.1.yaml');
	const data = await executePolicyEngineBackend(genState, 'banking_V0.1.yaml');
	const governanceResultTxt = data.engine_output;
	const governanceResult = jsyaml.load(governanceResultTxt);
	
	const executiveReportTxt = data.executive_summary;
	const executiveSumaryReport = jsyaml.load(executiveReportTxt);

	const analystReportTxt = data.analyst_report;
	const analystSumaryReport = jsyaml.load(analystReportTxt);

	const remediationReportTxt = data.remediation_plan;
	const remediationSumaryReport = jsyaml.load(remediationReportTxt);
		
    console.log("GOVERNANCE RESULT:", governanceResult);

    // 3. Store in assessment state (authoritative, frozen)
    assessmentState.gen = {
		controlState: Object.freeze(genState),
		controlGates: Object.freeze(governanceResult)
		//executiveReport: Object.freeze(executiveSumaryReport)
		//analystReport: Object.freeze(analystSumaryReport)
		//remediationReport: Object.freeze(remediationSumaryReport)
    };


    // 4. Build self-assessment summary
    let yamlContentSelfAssessment = "# Individual GEN answers\n";

    for (let i = 1; i <= 18; i++) {
      const qId = `GEN-Q${i}`;
      const answer = allAnswers.get(qId);
      yamlContentSelfAssessment += `${qId}: ${
        answer ? answer.answer : "not answered"
      } `;
    }

    // 5. Build governance YAML output (engine result)
    let yamlContent = "governance_results:\n";
    yamlContent += `  enforced_maturity_ceiling: ${governanceResult.enforcedMaturityCeiling}\n`;

//        return {
//            enforcedMaturityCeiling,
//            domainCaps,
//            materialGaps,
//            ceilingRationale,
//            confidenceLevel
//        };

    yamlContent += "  domain_caps:\n";
    for (const domain in governanceResult.domainCaps) {
      yamlContent += `    ${domain}: ${governanceResult.domainCaps[domain]}\n`;
    }

    yamlContent += "  material_gaps:\n";
    if (governanceResult.materialGaps.length === 0) {
      yamlContent += "    - none\n";
    } else {
      governanceResult.materialGaps.forEach(gap => {
        yamlContent += `    - "${gap}"\n`;
      });
    }

    yamlContent += "  ceiling_rationale:\n";
    governanceResult.ceilingRationale.forEach(reason => {
      yamlContent += `    - "${reason}"\n`;
    });

    yamlContent += `  confidence_level: ${governanceResult.confidenceLevel}\n`;
	
	yamlContent += `\nExecutive Summary:\n`;
	yamlContent += `${executiveSumaryReport.executive_narrative}\n`;
	
	yamlContent += `\nAnalyst Report:\n`;
	yamlContent += `${analystSumaryReport.analyst_narrative}`;	
	
	yamlContent += `\n\nRemediation Plan:\n`;

    const sections = {
        immediate_actions: remediationSumaryReport.remediation_plan?.immediate_actions || [],
        medium_term_actions: remediationSumaryReport.remediation_plan?.medium_term_actions || [],
        strategic_transformations: remediationSumaryReport.remediation_plan?.strategic_transformations || [],
        governance_dependencies: remediationSumaryReport.remediation_plan?.governance_dependencies || [],
        kpis_and_evidence: remediationSumaryReport.remediation_plan?.kpis_and_evidence || []
    };
	
	yamlContent += `IMMEDIATE ACTIONS (0-3 months):\n`;
    sections.immediate_actions.forEach((item, index) => {
        yamlContent += `${index + 1}. ${item}\n`;
    });


	yamlContent += `\nIMEDIUM TERM ACTIONS (3-9 months):\n`;
    sections.medium_term_actions.forEach((item, index) => {
        yamlContent += `${index + 1}. ${item}\n`;
    });

    yamlContent += `\nSTRATEGIC TRANSFORMATIONS (9-18 months)\n`;
    sections.strategic_transformations.forEach((item, index) => {
        yamlContent += `${index + 1}. ${item}\n`;
        //yamlContent += `   Gap: ${item.gap}\n`;
        //yamlContent += `   Owner: ${item.owner}\n`;
        //yamlContent += `   Timeline: ${item.timeline}\n`;
    });

    yamlContent += `\nGOVERNANCE DEPENDENCIES\n`;
    sections.governance_dependencies.forEach((item, index) => {
        yamlContent += `${index + 1}. ${item}\n`;
    });

    yamlContent += `\nKPIs AND EVIDENCE\n`;
    sections.kpis_and_evidence.forEach((item, index) => {
        yamlContent += `${index + 1}. ${item}\n`;
    });

    // 6. Show results in modal (NO AI YET)
    showGeneralQuestionAnswerModal(
      yamlContentSelfAssessment,
      yamlContent,
      "Governance scoring completed by deterministic policy engine."
    );

  } catch (err) {
    console.error("GEN Evaluation Failed:", err);
    alert("Error running maturity engine: " + err.message);
  } finally {
    generateAllBtn.textContent = "See Results";
    generateAllBtn.disabled = false;
  }
}

function summarizeAIResponseGen(){
	
  if (!assessmentState){
  }else if(!assessmentState.gen) {
  }else if(!assessmentState.gen.controlGates) {
  }

   let aiAgentResponse = "THE AGENT RESPONSE:\n";
	aiAgentResponse += `enforced_maturity_ceiling: ${assessmentState.gen.controlGates.enforcedMaturityCeiling}\n`;
	aiAgentResponse += `DomainCaps:`;
	aiAgentResponse += `  identityLifecycle: ${assessmentState.gen.controlGates.domainCaps.identityLifecycle}\n`;
	aiAgentResponse += `  accessGovernance: ${assessmentState.gen.controlGates.domainCaps.accessGovernance}\n`;
	aiAgentResponse += `  authenticationMFA: ${assessmentState.gen.controlGates.domainCaps.authenticationMFA}\n`;
	aiAgentResponse += `  privilegedAccess: ${assessmentState.gen.controlGates.domainCaps.privilegedAccess}\n`;
	aiAgentResponse += `  monitoringAndLogging: ${assessmentState.gen.controlGates.domainCaps.monitoringAndLogging}\n`;
	
	
	aiAgentResponse += `material_gaps:\n`;
	
	const gaps = normalizeMaterialGaps(assessmentState.gen.controlGates.materialGaps);
	if (!gaps){
		materialGaps = [];
		aiAgentResponse += `  ${materialGaps}\n`;
	}
	else if(Array.isArray(gaps)){
		let pos = 0;
		while(pos < gaps.length){
			let gapText = gaps[pos];
			aiAgentResponse += `  - ${normalizeHyphens(gapText)}\n`;
			pos = pos + 1;
		}
	}
	aiAgentResponse += `ceilingRationale:\n`;
	const rationale = normalizeMaterialGaps(assessmentState.gen.controlGates.ceilingRationale);
	if (!rationale){
		rationaleArary = [];
		aiAgentResponse += `  ${rationaleArary}\n`;
	}
	else if(Array.isArray(rationale)){
		let pos = 0;
		while(pos < rationale.length){
			let rationaleText = rationale[pos];
			aiAgentResponse += `  - ${normalizeHyphens(rationaleText)}\n`;
			pos = pos + 1;
		}
	}
	
	aiAgentResponse += `assessorGuidance:\n`;
	const guidance = normalizeMaterialGaps(assessmentState.gen.controlGates.assessorGuidance);
	if (!guidance){
		guidanceArary = [];
		aiAgentResponse += `  ${guidanceArary}\n`;
	}
	else if(Array.isArray(guidance)){
		let pos = 0;
		while(pos < guidance.length){
			let guidanceText = guidance[pos];
			aiAgentResponse += `  - ${normalizeHyphens(guidanceText)}\n`;
			pos = pos + 1;
		}
	}	
	
		
	aiAgentResponse += `gen_confidence_level: ${assessmentState.gen.controlGates.confidenceLevel}\n`;
	return aiAgentResponse;

}

function showGeneralQuestionAnswerModal(yamlContentSelfAssessment, yamlContent, aiAgentResponseGen) {
    // Remove existing modal if any
    const existingModal = document.querySelector('.yaml-modal');
    if (existingModal) {
        existingModal.remove();
    }
	
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'yaml-modal';
    modal.innerHTML = `
	        <div class="yaml-modal-content">
            <div class="yaml-header">
                <div class="yaml-title">Result</div>
                <button class="close-yaml">&times;</button>
            </div>
			<div class="yaml-content">YOUR SELECTION:\n${yamlContentSelfAssessment}</div>
			<div class="yaml-content">${yamlContent}</div>
			<div class="yaml-content">${aiAgentResponseGen}</div>
            <div class="yaml-actions">
                <button class="close-yaml-btn">Close</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Show modal
    modal.style.display = 'block';
    
    // Add event listeners
    const closeButtons = modal.querySelectorAll('.close-yaml, .close-yaml-btn');
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            modal.style.display = 'none';
			const generateAllBtn = document.getElementById('generateAllGenAnsBtn');
			generateAllBtn.textContent = "See Answer";
        });
    });
    
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
			const generateAllBtn = document.getElementById('generateAllGenAnsBtn');
			generateAllBtn.textContent = "See Answer";			
        }
    });
}

function backendMaturityEngine(yamlContent) {
	
    const userName = "SunilPK";
    const apiUrl = "http://localhost:8000/assess_new";	
    // RETURN the fetch promise
    return fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_name: userName,
            general_question: yamlContent
        })
    })
    .then(async response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        //const rawText = await response.text();
		//alert(rawText);
		const data = await response.json();
		//alert("ENGINE OUTPUT:\n" + data.engine_output);
		//alert("EXECUTIVE SUMMARY:\n" + data.executive_summary);
		//alert("ANALYST:\n" + data.analyst_report);
		//alert("REMEDIATION PLAN:\n" + data.remediation_plan);
		return data;
    })
    .catch(err => {
        console.error("Connection Error:", err);
        return "Error: " + err.message;  // Still return something
    });	
}

function testMaturityAPIGen(yamlContent) {
    const userName = "SunilPK";
    const generalQuestion = yamlContent;
    const apiUrl = "http://localhost:8000/assess";

    
    // RETURN the fetch promise
    return fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_name: userName,
            general_question: generalQuestion
        })
    })
    .then(async response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const rawText = await response.text();
        const yamlTextResp = jsyaml.load(rawText);
        assessmentState.gen.rawResponse = Object.freeze(yamlTextResp);
        const controlGateResult = extractGenControlGates(yamlTextResp);
        assessmentState.gen.controlGates = Object.freeze(controlGateResult);
        
        return JSON.stringify(controlGateResult, null, 2);
    })
    .catch(err => {
        console.error("Connection Error:", err);
        return "Error: " + err.message;  // Still return something
    });
}

function extractGenControlGates(genResponse) {
  if (!genResponse || !genResponse.gen_assessment) {
    throw new Error("Invalid GEN response structure");
  }

  const controlGates = {
    // Global governance ceiling (hard stop)
    enforcedMaturityCeiling: genResponse.gen_assessment.enforced_maturity_ceiling ?? null,

    // Per-domain hard caps (authoritative)
    domainCaps: {
      identityLifecycle: genResponse.domain_caps?.identity_lifecycle ?? null,
      accessGovernance: genResponse.domain_caps?.access_governance ?? null,
      authenticationMFA: genResponse.domain_caps?.authentication_mfa ?? null,
      privilegedAccess: genResponse.domain_caps?.privileged_access ?? null,
      monitoringAndLogging: genResponse.domain_caps?.monitoring_and_logging ?? null
    },

    // Supporting rationale (used in explanations, not scoring)
    materialGaps: genResponse.gen_assessment.material_gaps || [],
    ceilingRationale: genResponse.gen_assessment.ceiling_rationale || [],
    assessorGuidance: genResponse.assessor_guidance || [],
    confidenceLevel: genResponse.confidence_level || "Medium"
  };

  return controlGates;
}

// Function to update the global button state
function updateGenAnsButton() {
    const generateAllBtn = document.getElementById('generateAllGenAnsBtn');
    if (checkAllQuestionsAnswered()) {
        generateAllBtn.disabled = false;
        generateAllBtn.classList.add('enabled');
    } else {
        generateAllBtn.disabled = true;
        generateAllBtn.classList.remove('enabled');
    }
}

function setupRadioButtonListeners() {
    document.addEventListener('change', function(event) {
        if (event.target.type === 'radio') {
            const questionId = event.target.dataset.questionId;
            const value = event.target.value;
            const domain = event.target.dataset.domain;
            
            // Store the answer
            allAnswers.set(questionId, {
                questionId: questionId,
                answer: value,
                domain: domain
            });
            
            // Update the button state
            updateGenAnsButton();
			navigateQuestion("GEN", "next");
            
            // Optional: Show current answer status
            console.log(`Question ${questionId} = ${value}`);
        }
    });
}

function initializeGenResultButton(){
// Initialize everything when DOM is loaded
	setupRadioButtonListeners();
	const generateAllBtn = document.getElementById('generateAllGenAnsBtn');
	if (generateAllBtn) {
        generateAllBtn.addEventListener('click', generateFinalGenResult);
    }
}

function normalizeMaterialGaps(gaps) {
  if (!gaps) return [];

  if (Array.isArray(gaps)) {
	  return gaps.map(normalizeHyphens);
  }

  return gaps
    .split(',')
    .map(gap => normalizeHyphens(gap.trim()))
    .filter(Boolean);
}

function normalizeHyphens(text) {
  return text.replace(/[\u2010\u2011\u2012\u2013\u2014\u2212]/g, '-');
}

function scrollToAssessment() {
	const questionsContainer = document.getElementById('questions-container');
	if (questionsContainer) {
		questionsContainer.scrollIntoView({ behavior: 'smooth' });
        }
}

async function executePolicyEngineBackend(genState, yamlPath){
    try {
        // 1. Load YAML
        const response = await fetch(yamlPath);
        if (!response.ok) throw new Error("Failed to load YAML: " + response.status);
        const yamlText = await response.text();

        // 2. Parse YAML
        const policy = jsyaml.load(yamlText);
		
		// Let call backend to do the below calculation
		//alert(JSON.stringify(genState)); 
		//alert(yamlText);
		let yamlContent = "user_gen_question_answer:\n";
		yamlContent += "  " + JSON.stringify(genState);
		yamlContent += "\nRULES_TO_APPLY:\n";
		yamlContent += "  rules:\n";
		

		// Split yamlText into lines and indent each line with 2 spaces
		const indentedYaml = yamlText.split('\n')
		  .map(line => "    " + line)  // Add 2 spaces to each line
		  .join('\n');

		yamlContent += indentedYaml;
		const result = await backendMaturityEngine(yamlContent);
		return result;
    } catch (err) {
        console.error("Policy Engine Error:", err);
        return null;
    }	
}

async function executePolicyEngine(genState, yamlPath) {
    try {
        // 1. Load YAML
        const response = await fetch(yamlPath);
        if (!response.ok) throw new Error("Failed to load YAML: " + response.status);
        const yamlText = await response.text();

        // 2. Parse YAML
        const policy = jsyaml.load(yamlText);
		
        const materialGaps = [];
        const ceilingRationale = [];
        let enforcedMaturityCeiling = 5; // start with max maturity
        const domainCaps = {};
		const triggeredRules = {}; 

        // Helper: Evaluate triggers dynamically
        function evalTrigger(trig) {
            // Replace gen.Qx with corresponding boolean from genState
            const expr = trig.replace(/gen\.(Q\d+)/g, (_, q) => {
                if (q in genState) {
					return genState[q];
				}					
                console.warn(`Missing genState for ${q}, defaulting to false`);
                return false;
            });
            // Evaluate boolean expression
            return eval(expr);
        }

        // 3. Process governance rules
        const rules = policy.governance_rules;
        for (const ruleName in rules) {
            const rule = rules[ruleName];
            let triggered = false;
            if (rule.triggers && Array.isArray(rule.triggers)) {
                rule.triggers.forEach(trig => {
                    if (evalTrigger(trig)) {
                        triggered = true;
                        materialGaps.push(`Rule triggered: ${ruleName} -> ${rule.description}`);
                        ceilingRationale.push(`${ruleName}: Triggered. Ceiling reduced to ${rule.ceiling}`);
						triggeredRules[ruleName] = true;
                        enforcedMaturityCeiling = Math.min(enforcedMaturityCeiling, rule.ceiling);
                    }
                });
            }
        }

        // 4. Compute domain caps
        const domains = policy.domain_caps;
        for (const domainName in domains) {
            let domainCeiling = 5; // max
            const governedBy = domains[domainName].governed_by;
            governedBy.forEach(ruleName => {
                if (triggeredRules[ruleName] === true) {
                    domainCeiling = Math.min(domainCeiling, rules[ruleName].ceiling);
                }
            });
            domainCaps[domainName] = domainCeiling;
        }


        // 5. Determine confidence level (simple example)
        let confidenceLevel = "High";
        if (materialGaps.length > 2) confidenceLevel = "Medium";
        if (materialGaps.length > 5) confidenceLevel = "Low";
        return {
            enforcedMaturityCeiling,
            domainCaps,
            materialGaps,
            ceilingRationale,
            confidenceLevel
        };

    } catch (err) {
        console.error("Policy Engine Error:", err);
        return null;
    }
}

function NowRunEngine(fileContents, genState) {
    const policy = jsyaml.load(fileContents);

    const governanceRules = policy.governance_rules || {};
    const domainCapsDef = policy.domain_caps || {};

    const materialGaps = [];
    const ceilingRationale = [];
    const domainCaps = {};

    // Iterate over domains
    for (const [domain, domainInfo] of Object.entries(domainCapsDef)) {
        const governedBy = domainInfo.governed_by || [];
		
        let domainCeiling = Infinity;

        for (const ruleName of governedBy) {
            const rule = governanceRules[ruleName];
            if (!rule) continue;

            const triggers = rule.triggers || [];
            const ruleCeiling = rule.ceiling || 5;

            let triggered = false;

            triggers.forEach(trig => {
                try {
                    // Convert trigger like 'gen.Q1 == false' dynamically
                    let evalExpr = trig.replace(/gen\.Q1/g, genState.authoritativeHR)
                                       .replace(/gen\.Q10/g, genState.lifecycleAutomation)
                                       .replace(/gen\.Q11/g, genState.lifecycleAutomation)
                                       .replace(/gen\.Q12/g, genState.lifecycleAutomation)
                                       .replace(/gen\.Q13/g, genState.disconnectedApps);
					
                    if (eval(evalExpr)) {
                        triggered = true;
                        materialGaps.push(`Rule triggered: ${ruleName} -> ${rule.description || ''}`);
                        ceilingRationale.push(`${ruleName}: Triggered. Ceiling reduced to ${ruleCeiling}`);
                        domainCeiling = Math.min(domainCeiling, ruleCeiling);
                    }
                } catch (err) {
                    console.error(`Error evaluating trigger ${trig}:`, err);
                }
            });
        }

        if (domainCeiling === Infinity) domainCeiling = 5;
        domainCaps[domain] = domainCeiling;
					
    }

    // Overall enforced maturity ceiling
    const enforcedMaturityCeiling = Math.min(...Object.values(domainCaps));
	

    // Confidence level
    const confidenceLevel = Object.values(domainCaps).every(v => v >= 3) ? "High" : "Medium";
	return {
        enforcedMaturityCeiling,
        domainCaps,
        materialGaps,
        ceilingRationale,
        confidenceLevel
    };
}
