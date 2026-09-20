**Group No**: 1



**Name/s**: Aldrin Jose V, Peña, Christine B. Owapin, Shenerlyn A. Edem, Lawrence Torres, Andrew Nicos Biglang-awa



**Research Topic/Problem/Variables Proposal:** Network Configuration Evaluation and Topology Discovery Tool



**Chapter I**



**THE PROBLEM AND ITS BACKGROUND**



**Introduction**



The global landscape of Information and Communications Technology (ICT) is currently defined by an unprecedented shift toward automation and intelligent infrastructure management. In a 2024 report by Gartner, it was emphasized that over 65% of enterprise networking activities will be automated by 2026 to mitigate the risks associated with human error and manual intervention. Globally, network downtime remains a critical economic threat, with industry observations suggesting that manual configuration errors account for nearly 80% of total network failures (Li et al., 2024). International standards, such as those set by the IEEE and the Cisco Networking Academy, increasingly stress the necessity of precise configuration and real-time topology awareness to maintain secure digital environments. This transition is further evidenced by the evolution of the Cisco certification roadmap, which, effective February 2026, officially migrates traditional DevNet and core tracks into specialized CCNA, CCNP, and CCIE Automation certifications (Cisco, 2026). As organizations worldwide transition to Software-Defined Networking (SDN), the ability to evaluate network health and discover topologies automatically has moved from being a luxury to an operational requirement.



In the national context of the Philippines, the push for digital transformation is evident in both the corporate and academic sectors. The Department of Information and Communications Technology (DICT) has outlined a 2026 Growth Agenda, positioning the digital economy to contribute up to 12% of the national GDP through infrastructure modernization and high-quality tech job creation (DICT, 2026). This requires a workforce highly skilled in automated network management. However, many local institutions still struggle with traditional, labor-intensive methods of network assessment. At First City Providential College (FCPC), a recognized Cisco-partnered institution, this problem is observed firsthand during laboratory assessments where instructors manually verify Command Line Interface (CLI) outputs. According to local observations within the ICT department, manual checking for large batches of students leads to delayed feedback loops and subjective grading inconsistencies. This delay often prevents students from achieving immediate mastery of configuration tasks, which is essential for their future competitiveness in the Philippine tech industry.



The research gap in this field lies in the specific application of network automation within the pedagogical or educational setting. While recent literature by authors like Verma et al. (2023) explores complex enterprise-level network monitoring using blockchain and machine learning, there is a notable scarcity of studies focusing on automated grading and topology discovery tools designed specifically for classroom environments. Most commercial tools remain high-cost and optimized for large-scale data centers rather than the structured, educational needs of a Cisco Academy lab. Furthermore, previous research often neglects the challenges faced by instructors in managing diverse student configuration outputs that, while functionally correct, may vary in syntax. This study addresses this unresolved issue by developing a tool that provides consistent, objective, and immediate feedback for student-led network configurations. By shifting the focus from enterprise maintenance to educational evaluation, this research fills a critical void in academic ICT management.



The institutional and legal basis for this study is rooted in several Philippine mandates and educational policies that promote the advancement of ICT skills. Republic Act No. 10844, also known as the "Department of Information and Communications Technology Act of 2015," mandates the state to promote the development and use of ICT in education. Additionally, the DepEd ICT Strategic Plan 2022–2026 emphasizes the automation of core systems to modernize education management and improve teaching quality (DepEd, 2022). Within the framework of First City Providential College, school policies regarding the enhancement of the Cisco Networking Academy program align with this study’s goal of optimizing laboratory efficiency. These legal and institutional directives provide the necessary authority to implement automated tools that ensure students meet both national and international competency standards. By automating the evaluation process, the institution complies with the government's call for a more digitally inclusive and technologically advanced educational system.



**Conceptual Framework**



The framework of this research used the Development-Implement-Evaluation (IDE) model. The IDE model presents an effective structure for guiding systems through their creation, deployment, and performance assessment phases. To secure if these systems are within accordance with the required legal policies, we followed the national ICT policies.



The policies utilized in this research are: the R.A 10844 Department of Information and Communications Technology (DICT) Act of 2015 which promotes the upgrading and defense of ICT infrastructure in support of national development objectives, providing direction to use technology in securing the national infrastructure from being misused; and R.A. No. 10173, which provides legal and administrative guidelines on information privacy in the Philippines and establishes legal and ethical requirements on managing and preserving the confidentiality, integrity, and availability of sensitive network information. With the combination of both policies and regulations, this study will use a secure automatic monitoring system structured around the IDE framework.



In addition, the project aligns with United Nations Sustainable Development Goal (SDG) 4: Quality Education, by ensuring inclusive and equitable quality education and promoting lifelong learning opportunities through automated, objective feedback mechanisms in technical laboratories. It also supports SDG 9: Industry, Innovation, and Infrastructure, by modernizing educational infrastructure through digital tools and reliable network management practices.



**![](data:image/png;base64...)**



**Figure 1. Paradigm of the Study**



Figure 1 shows the configuration evaluation process, which begins with the upload of the device’s network configuration. Evaluation criteria are then defined by the teacher or proctor. The configuration data, together with the established criteria, are fed into a pre-trained large language model (LLM). The model analyzes the configuration based on the specified criteria and produces an evaluation output, which may include recommendations, identified misconfigurations, or compliance assessments. This process concludes with an evaluative result that assists network administrators in improving configuration quality and reliability.



**Statement of the Problem**



This study aims to determine how a Networking Configuration Assistant can improve the reliability and accuracy of network configuration evaluation. Specifically, it seeks to answer the following questions:



1. Analyze current manual evaluation methods in terms of implemented security configurations, missed configurations, and actual task completion.

2. Design and synthesize an automated network configuration evaluation and topology discovery tool to standardize grading criteria.

3. Evaluate the effectiveness of the Network Configuration Assistant in terms of configuration checking accuracy, grading consistency, and feedback reliability.

4. Utilize the evaluation results to formulate administrative recommendations and institutional guidelines for optimizing network laboratory instruction.



Aligned with the objectives stated above, this study answers the following research questions:



1. How are student network configurations currently evaluated manually in terms of:

2. Security configurations implemented

3. Number of configurations missed based on given instructions

4. Actual task completion

5. How effective is the Network Configuration Assistant in improving the consistency of marks according to different criteria?

6. What are the different functionalities of the Network Configuration Assistant, and how do they contribute to improving overall network configuration evaluation?

7. How effective is the Networking Configuration Assistant in improving network configuration evaluation in terms of:

8. Accuracy of configuration checking

9. Consistency of grading results

10. Reliability of generated feedback



**SCOPE**



The scope of this study centers on the development of an automated system designed to streamline the evaluation of network laboratory activities at First City Providential College. Specifically, the system is engineered to perform three primary functions: the automated discovery of simple network topologies, the verification of network configurations by analyzing device running-config files, and the execution of basic troubleshooting to identify connectivity issues. The research will be conducted during the Academic Year 2026–2027, utilizing a qualitative research approach to assess the system's impact on the learning environment.



The primary respondents for this study are network engineering students, whose interaction with the tool will provide the data necessary to evaluate its effectiveness in providing immediate, objective feedback during practical assessments.



**DELIMITATION**



While the system aims to modernize laboratory procedures, it is subject to several key delimitations to ensure a focused research outcome. The application is strictly designed for small-scale networks and does not extend to the management of large-scale enterprise infrastructures or high-density data centers. Furthermore, the system evaluates device configuration and inter-device consistency rather than live network behaviour; it does not extend to Software-Defined Networking (SDN) controllers or scripted orchestration platforms. Geographically and institutionally, the study is confined to the Cisco Networking Academy lab at First City Providential College, and its results may not be generalized to other vendors’ hardware platforms, as the tool is optimized specifically for standard Cisco CLI outputs.



**SIGNIFICANCE OF THE STUDY**



The objective of this study is to increase the amount of knowledge available regarding network monitoring and automation in schools by making use of a web-based monitoring system that is driven by Python and includes automated first-aid troubleshooting procedures. It looks at the issues associated with manual network monitoring at First City Providential College. The study provides practical and data-based recommendations which other organisations facing similar legacy network configurations and operational difficulties can make use of.



The importance of this work lies in the fact that it provides a practical guide to ICT administrators and system developers on how to deploy automated systems based on the Development-Implement-Evaluation (DIE) framework. It is also of value to educational leaders since it offers a monitoring framework that satisfies the legal requirements set out in R.A. 10844 (the DICT Act of 2015). For network users and other stakeholders, it ensures compliance with R.A. No. 10173 (the Data Privacy Act of 2012) in order to securely protect sensitive information. Lastly, it acts as a foundational reference and empirical baseline for future researchers who wish to carry out further studies on Python-driven automation and policy-compliant ICT system design.



**To Students**



Students will be able to review their configurations, and the networking configuration assistant helps the students to identify specific errors in their network configurations, such as incorrect VLAN settings, routing protocols, and security policies.



**To Teachers**



Teachers will have a much easier time grading students’ configurations and more efficiently. Teachers benefit from automated validation of student configurations, enabling faster, more consistent grading. The assistant highlights deviations from correct setups, allowing instructors to provide targeted feedback and spend less time on manual checks, improving overall teaching efficiency.



**DEFINITION OF TERMS**



The following terms were defined conceptually and operationally:



**Network configuration Assistant**



Refers to the automated system developed in this study that analyzes and evaluates students’ network device configurations. It guides users in setting up and troubleshooting network configurations by checking inputs and providing structured feedback based on predefined criteria.



**Topology Discovery**



refers to the process of identifying and mapping the logical and physical structure of a network from configuration files. It allows the system to understand device relationships and validate configurations based on the intended network design.



**Missed Configurations**



Refers to the number required network settings or parameters that a student failed t o implement correctly or completely based on the given configurations instructions. This serves as a measurable indicator used to compare the detection capability of the system against manual evaluation.



**Manual Evaluation**



refers to the traditional method of assessing students network configurations where an instructor reviews and grades student outputs based on established criteria. This serves as the baseline method for comparison in this study.



**Chapter II**



**Review of Related Literature and Studies**



This chapter presents the reviewed literature relevant and pertinent to the present study. The materials consist of books, online articles, electronic resources, scholarly journals, and other reading materials that enabled the researcher in the conceptualization and operationalization of this research endeavor.



**Conceptual Literature**



This section of the chapter provides a discussion of concepts, constructs, principles, and models sourced from books, journals, and electronic resources presented in thematic titles. The reviewed conceptual literature establishes that manual evaluation models are increasingly unsustainable for complex technical outputs. Concepts surrounding software-defined automation, automated assessment systems, and algorithmic topology inference confirm that automated rule-based frameworks provide the structural foundation needed for scalable educational evaluation. While enterprise solutions exist, their lack of integration into pedagogical workflows creates an unaddressed gap that this study resolves.



**Software-Defined Network**



A *Software-Defined Network* (SDN) controller needs comprehensive visibility of the whole network to provide effective routing and forwarding decisions in the data layer. Nevertheless, the topology discovery service in the SDN controller is vulnerable to the *Topology Poisoning Attack (TPA)*, which targets corrupting the controller’s view on the connected devices (e.g., switches or hosts) to the network and inter-switch link connections. The attack could cause dramatic impacts on the network’s forwarding policy by changing the traffic path and even opening doors for *Man-in-the-Middle (MitM) and Denial of Service (DoS)* attacks. Recent studies presented sophisticated types of TPA, which could successfully bypass several well-known defence mechanisms for SDN. Nonetheless, the scientific literature lacks a comprehensive review and survey of existing TPAs against topology discovery services and corresponding defence mechanisms.



Nevertheless, SDN principles amplify the importance of security due to its centralized control, creating a single point of failure that must be safeguarded against attacks. SDN’s dynamic, programmable nature introduces new attack vectors, making it essential to protect against potential vulnerabilities that can compromise network traffic and configurations. Additionally, the automation and agility inherent in SDN can lead to rapid network changes, necessitating stringent security measures to prevent misconfigurations and unauthorized access, which can disrupt network operations and compromise data integrity. Two critical factors underscore the importance of SDN security.



**Network Configuration and Automation**



Network configuration is fundamentally defined as the strategic assignment of parameters, protocols, and settings to network devices to enable and govern system-wide communication. Modern literature emphasizes a shift toward network automation, which Selector AI (2025) describes as the utilization of software-based tools to manage infrastructure through pre-defined policies rather than manual intervention. This evolution is necessitated by the increasing complexity of organizational systems, leading to the emergence of "zero-touch" automation, where El Rajab et al. (2024) argue that networks are moving toward self-management and self-configuration with minimal human oversight. Consequently, network configuration is no longer just about individual device settings but has expanded to include automated validation and compliance enforcement, ensuring that the entire system adheres to intended operational standards.



A critical consensus across current research is that traditional, manual configuration methods are inherently prone to human error, creating significant security and operational vulnerabilities. For instance, reports from the World Journal of Advanced Research and Reviews (2025) shows that configuration errors are a major contributor to security incidents in global data breaches, with organizations relying on manual processes facing four times as many incidents as their automated counterparts. This is supported by Bringhenti et al. (2022), who demonstrated that automated tools in virtual environments drastically reduce misconfigurations compared to human effort. These findings bridge the gap between enterprise-level Intent-Based Networking (IBN)—where high-level operational goals are automatically translated into technical settings (Falkner & Apostolopoulos, 2022; Yu et al., 2024)—and the pedagogical application in this study. By mapping "instructor intent" (assigned tasks) against student "implementation" (configuration files), the Network Configuration Assistant mirrors the programmatic validation and error-reduction logic used in professional network management systems.



**Automated Assessment Systems**



Automated Assessment Systems (AAS) are fundamentally defined as software-based frameworks that evaluate learner outputs against established benchmarks without the need for constant human oversight. According to Messer et al. (2024), these systems have transitioned from basic output matching to sophisticated platforms utilizing static and dynamic analysis to assess technical correctness, style, and maintainability. A primary driver for their adoption, as emphasized by Stone and Rebelsky (2024), is scalability. As enrollment in complex computing courses grows, AAS provides the rapid feedback and large-scale marking capabilities that human instructors often struggle to sustain. This study aligns with these foundations by providing a tool capable of concurrent evaluation, ensuring that high volumes of student work do not compromise the speed or quality of feedback.



The literature consistently highlights that while manual grading is prone to fatigue and inter-rater variability, automated systems offer a level of precision and efficiency that mirrors human performance while saving significant time. Research by Ahmed et al. (2022) and Elbourhamy et al. (2025) demonstrates that AI-driven and automated tools achieve high accuracy in objective technical assessments, effectively reducing evaluator fatigue and improving scoring consistency. This is particularly relevant in the context of simulation-based learning, where platforms like Cisco Packet Tracer allow students to build complex virtual networks that simulate real-world scenarios (Asadi et al., 2024; Sifiso & Muedini, 2024). These studies confirm that such tools enhance practical skills, especially in resource-constrained environments. The Network Configuration Assistant serves as the critical evaluative layer for these environments; by interpreting and validating configuration outputs, it ensures that student implementations are assessed through a reliable, programmatic lens that eliminates the oversights common in manual inspection.



**Network Topology Discovery**



Network topology discovery is the systematic process of mapping the devices and structural relationships within a network to ensure connectivity and detect misconfigurations. In live environments, this is typically achieved through protocols like the Link Layer Discovery Protocol (LLDP) and the Cisco Discovery Protocol (CDP), which allow devices to advertise their identity and neighbors to one another. Systems like NetXMS and OpenNMS aggregate data from these protocols, along with Spanning Tree and Forwarding Database (FDB) tables, to build a comprehensive map. A critical principle in this process is bidirectional verification: a connection between two nodes is only confirmed when both endpoints agree on the relationship, ensuring the accuracy of the resulting network map.



In educational or static environments where live traffic is unavailable, topology discovery must be adapted into a process of logical inference from configuration files. Instead of querying a live device, the system parses static statements regarding interface assignments, IP addresses, and neighbor declarations to reconstruct the intended network design. By reconstructing the topology from these files, an automated tool can evaluate student submissions not just as isolated commands, but as functional components within a correctly situated and interconnected network architecture.



**Synthesis of Conceptual Literature**



The reviewed conceptual literature provides a cohesive and mutually reinforcing theoretical foundation for the Network Configuration Evaluation and Topology Discovery Tool. Across all three thematic areas, a dominant and consistent theme emerges: manual, human-driven processes are increasingly inadequate in contexts characterized by scale, complexity, and the need for reliable, repeatable outcomes. In the domain of network configuration and automation, the literature demonstrates that automated, rule-based systems consistently outperform manual methods in speed, consistency, and error detection (Selector AI, 2025; Bringhenti et al., 2022; El Rajab et al., 2024). In the domain of automated assessment, scholars affirm that AATs provide scalable, reproducible, and timely evaluation of technical outputs in educational contexts, while acknowledging limitations where tasks involve nuanced judgment (Messer et al., 2024; Stone & Rebelsky, 2024; Elbourhamy et al., 2025). In the domain of network topology discovery, the literature establishes that topology can be systematically derived from device-level data through algorithmic. A critical gap identified across all three areas is the absence of a purpose-built tool that integrates these principles specifically for the evaluation of student-produced network device configurations in a pedagogical context. Existing automated assessment tools focus on programming assignments and text responses; existing topology discovery tools focus on live networks; and existing configuration automation frameworks target enterprise deployment rather than educational evaluation. The present study directly addresses this intersection, making a distinct and original contribution to each of the three reviewed conceptual domains.



**Research Literature**



Data consisting of professional literature and research studies particularly taken from peer-reviewed materials accessed online were presented and highlighted in this part of the chapter. Empirical studies consistently validate that automated configuration checking and algorithmic topology mapping drastically reduce error rates and administrative overhead while maximizing scoring consistency. Although previous research heavily investigates enterprise automation and standalone educational grading tools separately, empirical evidence supporting a unified, classroom-oriented network configuration evaluation assistant remains sparse. This study builds directly upon these validated methodologies to bridge the pedagogical gap.



**Network Configuration and Automation**



Automation in network configuration significantly outperforms manual methods by enhancing speed, precision, and reliability. Empirical research, such as the study by Mazin and Rahman (2023), reveals that Python-based automation can reduce configuration time across complex environments. These benefits extend to enterprise-grade tools like Ansible and SaltStack, which consistently improve deployment speed regardless of whether physical or virtual hardware is used. Beyond mere speed, AI-driven validation tools have been shown to reduce change-related outages by over 87%, as they eliminate common human errors and policy violations that typically arise during manual entry.



In a technical or educational context, these advancements shift the focus from repetitive task execution to high-level architectural management. Research into heterogeneous and multi-vendor environments demonstrates that automation minimizes the cognitive burden on administrators by streamlining the configuration of complex routing protocols like IGP and EGP. For instructors, this translates into a more scalable evaluation process; by using tools that mirror enterprise compliance-checking logic, educators can systematically identify student errors that might be overlooked during a manual review. This approach not only ensures consistent grading across large cohorts but also prepares students for a professional landscape where automated synthesis and validation are the industry standards.



**Automated Assessment in Computing Education**



Research into Automated Assessment Tools (AATs) highlights their transformative impact on computing education, particularly through improved evaluation quality and student satisfaction. Studies by Messer et al. (2024) underscore a dual-analysis paradigm that combines static analysis—verifying code structure and parameters—with dynamic analysis to test behavioral correctness. This method ensures faster, more consistent feedback than manual grading, which is often limited by human factors. Empirical evidence from Liu (2024) supports this, showing that automated platforms can achieve over 80% student satisfaction while notably boosting academic performance. By automating the assessment of well-structured tasks, institutions can eliminate the inter-rater variability and evaluator fatigue identified by Koubaa and Khan (2024), resulting in a fairer and more reliable grading process for large student cohorts.



In the specialized field of networking education, automation addresses the critical bottleneck of evaluating complex, simulation-based assignments. While tools like Cisco Packet Tracer enhance procedural understanding and student scores (Asadi et al., 2024), the manual review of intricate configuration files remains a significant challenge for instructors. Sifiso and Muedini (2024) found that while students value simulation for professional readiness, the sheer volume of technical outputs often exceeds instructor capacity for individual feedback. Automated systems solve this by performing systematic structural validation and topology checks, allowing for the rigorous evaluation of device configurations and protocol implementations. This capability not only maintains high pedagogical standards but also frees educators from repetitive manual tasks, allowing them to focus on high-level instruction.



**Network Topology Discovery in Research**



Research into automated network topology discovery has shifted toward sophisticated algorithmic inference, enabling systems to reconstruct network structures even from partial or inconsistent data. Studies like those by Kashyap et al. (2024) demonstrate that dual-module systems can accurately map architectures by leveraging inference rules, a capability that is vital when analyzing student submissions that may contain errors. Similarly, the work of Gouel et al. (2022) proves that systematic probing and algorithmic approaches can yield comprehensive maps even under limited observability. This capacity for logical inference allows automated tools to move beyond simple text-matching, instead deriving the "intended" network design from the fragments of information available within configuration archives.



In practice, this discovery process relies on extracting local neighbor information and routing relationships to build a global view of the network. As noted by Sun (2022) and Alfaresa et al. (2023), protocols such as OSPF and BGP neighbor statements inherently encode the structural DNA of a network.This topology-aware design is a significant advancement over isolated checkers; it allows the system to evaluate settings within their relational context, identifying errors that only surface when considering the interactions between multiple devices. By reconstructing the network map first, automated assistants can verify if individual parameters collectively produce the intended, functional topology.



**Synthesis of Research Literature**



The research literature reviewed across all three thematic areas converges on a consistent and well-supported conclusion: automated tools that systematically apply rule-based or algorithmic evaluation to technical outputs outperform manual approaches in speed, consistency, accuracy, and scalability, particularly in educational and operational settings involving high volumes of structured technical submissions. Empirical research on network configuration automation (Mazin & Rahman, 2023; Nilsson & Persson, 2022; Datta et al., 2023) demonstrates that automation reduces errors and time costs dramatically, even in complex multi-device environments. Research on automated assessment in computing education (Messer et al., 2024; Elbourhamy et al., 2025; Liu, 2024) provides robust experimental evidence that automated grading is both more consistent and more scalable than manual evaluation for objective, technically-defined tasks. Research on network topology discovery (Kashyap et al., 2024; Sun, 2022; Gouel et al., 2022) establishes that topology can be reliably inferred from partial or file-based data through structured algorithms, validating the methodology employed in the present tool's topology discovery component. A clear gap identified across the reviewed studies is the absence of empirical research on tools that specifically combine configuration file parsing, topology inference, and automated missed-configuration detection for use in networking education. While individual studies address automated assessment, network automation, and topology discovery in isolation, no reviewed study integrates all three in a system designed to evaluate student-produced device configurations. The Network Configuration Evaluation and Topology Discovery Tool developed in this study directly addresses this gap, with the reviewed research providing both empirical support for the tool's core mechanisms and a benchmark against which its effectiveness can be compared.



**Chapter III**



**Technical Background**



This chapter examines the existing network management setup at First City Providential College alongside the proposed Network Configuration Evaluation and Topology Discovery Tool. It analyzes the technical framework supporting the institution’s local area network, detailing the hardware assets, software dependencies, user roles, and network protocols currently in place

